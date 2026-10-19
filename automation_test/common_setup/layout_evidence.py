"""Explicit UI-review evidence; collection success is never a visual PASS gate."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from playwright.sync_api import Page


ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "ui-review"
VIEWPORT_WIDTHS = (320, 360, 390, 430, 768, 1024, 1366)

# Text ranges catch painted text outside its element's box (e.g. an unbroken
# note). Element bounds alone miss this, even when documentWidth stays small.
MEASURE_LAYOUT = r"""({cardSelector, intentionalScrollSelectors, intentionalVerticalScrollSelectors}) => {
  const tolerance = 1.5;
  const rect = r => ({left:r.left, top:r.top, right:r.right, bottom:r.bottom,
                     width:r.width, height:r.height});
  const visible = e => {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    // Chromium can retain layout boxes for unpainted content of closed details.
    // Only the summary is painted until opened; expanded content is still measured.
    for (let parent=e.parentElement; parent; parent=parent.parentElement) {
      if (parent.tagName==='DETAILS' && !parent.open) {
        const summary=[...parent.children].find(child=>child.tagName==='SUMMARY');
        if (!summary || !summary.contains(e)) return false;
      }
    }
    return r.width > 0 && r.height > 0 && s.display !== 'none' &&
           s.visibility !== 'hidden' && s.visibility !== 'collapse';
  };
  const allowed = (e,card=null) => intentionalScrollSelectors.find(selector => {
    const region=e.closest(selector);
    // A scroll container must itself fit the viewport; only its contents can
    // legitimately sit offscreen. Inside-card checks still inspect the card.
    return region && (card || region !== e) && (!card || card.contains(region)) &&
      ['auto','scroll'].includes(getComputedStyle(region).overflowX) && region.scrollWidth>region.clientWidth;
  }) || null;
  const verticalRegion = (e,card) => {
    for (const selector of intentionalVerticalScrollSelectors) {
      const region=e.closest(selector);
      if (region && card.contains(region) &&
          ['auto','scroll'].includes(getComputedStyle(region).overflowY) && region.scrollHeight>region.clientHeight)
        return region;
    }
    return null;
  };
  const outsideCard = (r,b,e,card) =>
    ((r.left < b.left-tolerance || r.right > b.right+tolerance) && !allowed(e,card)) ||
    ((r.top < b.top-tolerance || r.bottom > b.bottom+tolerance) && !verticalRegion(e,card));
  const intersect = (a,b) => Math.min(a.right,b.right)-Math.max(a.left,b.left)>tolerance &&
                           Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>tolerance;
  const describe = e => ({tag:e.tagName.toLowerCase(), testId:e.getAttribute('data-testid'),
                          role:e.getAttribute('role')});
  const cards = [...document.querySelectorAll(cardSelector)].filter(visible);
  const boxes = cards.map(e => e.getBoundingClientRect());
  const cardResults = cards.map((card,index) => {
    const bounds = boxes[index], violations = [], paints = [];
    const walker = document.createTreeWalker(card,NodeFilter.SHOW_TEXT);
    for (let node=walker.nextNode(); node; node=walker.nextNode()) {
      if (!node.textContent.trim() || !node.parentElement || !visible(node.parentElement)) continue;
      const element = node.parentElement, excludedBy = allowed(element,card);
      const range = document.createRange(); range.selectNodeContents(node);
      for (const r of range.getClientRects()) {
        if (r.width <= 0 || r.height <= 0) continue;
        paints.push({r,element});
        if (outsideCard(r,bounds,element,card))
          violations.push({kind:'text-outside-card',element:describe(element),bounds:rect(r)});
        for (let parent=element; parent && card.contains(parent); parent=parent.parentElement) {
          const style=getComputedStyle(parent), p=parent.getBoundingClientRect();
          // Ignore the document's vertical scroll, but detect clipped content
          // inside the card, including intentional truncation until explicitly reviewed.
          const clipX=['hidden','clip','auto','scroll'].includes(style.overflowX);
          const clipY=['hidden','clip','auto','scroll'].includes(style.overflowY);
          const horizontal=clipX && (r.left < p.left-tolerance || r.right > p.right+tolerance);
          const vertical=clipY && parent !== verticalRegion(element,card) &&
            (r.top < p.top-tolerance || r.bottom > p.bottom+tolerance);
          if ((!excludedBy && horizontal) || vertical) {
            violations.push({kind:'text-clipped',element:describe(element),
                             clipper:describe(parent),bounds:rect(r),clipBounds:rect(p)});
            break;
          }
        }
      }
    }
    const controls=[...card.querySelectorAll('button,input,select,textarea,[role=button]')].filter(visible);
    for (let i=0;i<controls.length;i++) {
      const a=controls[i], aRect=a.getBoundingClientRect();
      paints.push({r:aRect,element:a});
      if (outsideCard(aRect,bounds,a,card))
        violations.push({kind:'control-outside-card',element:describe(a),bounds:rect(aRect)});
      for (let j=i+1;j<controls.length;j++) {
        const b=controls[j];
        if (!a.contains(b) && !b.contains(a) && intersect(aRect,b.getBoundingClientRect()))
          violations.push({kind:'controls-overlap',element:describe(a),other:describe(b)});
      }
    }
    for (let i=0;i<paints.length;i++) {
      for (let j=i+1;j<paints.length;j++) {
        const a=paints[i], b=paints[j];
        if (a.element===b.element || a.element.contains(b.element) || b.element.contains(a.element)) continue;
        if (!allowed(a.element,card) && !allowed(b.element,card) && intersect(a.r,b.r))
          violations.push({kind:'content-overlap-within-card',element:describe(a.element),other:describe(b.element)});
      }
    }
    for (let j=0;j<cards.length;j++) {
      if (j===index || card.contains(cards[j]) || cards[j].contains(card)) continue;
      if (intersect(bounds,boxes[j])) violations.push({kind:'cards-overlap',otherIndex:j});
      for (const paint of paints) {
        if (!allowed(paint.element,card) && intersect(paint.r,boxes[j])) {
          violations.push({kind:'content-overlaps-other-card',otherIndex:j,
                           element:describe(paint.element),bounds:rect(paint.r)});
          break;
        }
      }
    }
    return {index,testId:card.getAttribute('data-testid'),bounds:rect(bounds),
            scrollWidth:card.scrollWidth,clientWidth:card.clientWidth,
            violationCount:violations.length,violations:violations.slice(0,80)};
  });
  const viewportOutside=[];
  for (const e of document.querySelectorAll('main *,header *,[role=dialog] *')) {
    if (!visible(e)) continue;
    const r=e.getBoundingClientRect();
    if (r.left < -tolerance || r.right > innerWidth+tolerance)
      viewportOutside.push({...describe(e),bounds:rect(r),excludedBy:allowed(e)});
  }
  const dialogs=[...document.querySelectorAll('[role=dialog]')].filter(visible).map(e => ({
    ...describe(e),bounds:rect(e.getBoundingClientRect()),scrollHeight:e.scrollHeight,clientHeight:e.clientHeight,
    focusInside:e.contains(document.activeElement),
    scrollRegions:[...e.querySelectorAll('*')].filter(n => visible(n) &&
      ['auto','scroll'].includes(getComputedStyle(n).overflowY)).map(n => ({
        ...describe(n),bounds:rect(n.getBoundingClientRect()),scrollHeight:n.scrollHeight,clientHeight:n.clientHeight}))
  }));
  return {viewport:{width:innerWidth,height:innerHeight},
          documentWidth:document.documentElement.scrollWidth,
          documentHeight:document.documentElement.scrollHeight,
          viewportOutsideCount:viewportOutside.filter(e=>!e.excludedBy).length,
          viewportOutside:viewportOutside.filter(e=>!e.excludedBy).slice(0,80),
          intentionalViewportOutside:viewportOutside.filter(e=>e.excludedBy).slice(0,80),
          cards:cardResults,cardCount:cardResults.length,cardSelector,
          measurementStatus:cardResults.length ? 'measured' : 'no-targets',dialogs,
          cardViolationCount:cardResults.reduce((sum,c)=>sum+c.violationCount,0),
          intentionalScrollSelectors,intentionalVerticalScrollSelectors};
}"""


def measure_layout(
    page: Page,
    *,
    card_selector: str = '[data-layout-card="booking"]',
    intentional_scroll_selectors: tuple[str, ...] = (),
    intentional_vertical_scroll_selectors: tuple[str, ...] = (),
) -> dict:
    return page.evaluate(MEASURE_LAYOUT, {
        "cardSelector": card_selector,
        "intentionalScrollSelectors": list(intentional_scroll_selectors),
        "intentionalVerticalScrollSelectors": list(intentional_vertical_scroll_selectors),
    })


def artifact_directory(task: str) -> Path:
    """Use only the runner's UUID; never overwrite the historical baseline."""
    run_id = os.environ.get("SPAOS_QA_RUN_ID", "")
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError("non-canonical run ID")
    except ValueError as error:
        raise RuntimeError("Layout evidence requires the QA runner's SPAOS_QA_RUN_ID UUID") from error
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,70}", task):
        raise ValueError("Artifact task name must be a short path-safe identifier")
    destination = ARTIFACT_ROOT / run_id / task
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def capture_layout(
    page: Page,
    *,
    task: str,
    label: str,
    role: str,
    dataset: dict,
    card_selector: str = '[data-layout-card="booking"]',
    intentional_scroll_selectors: tuple[str, ...] = (),
    intentional_vertical_scroll_selectors: tuple[str, ...] = (),
    full_page: bool = True,
) -> dict:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,70}", label):
        raise ValueError("Artifact label must be a short path-safe identifier")
    evidence = measure_layout(page, card_selector=card_selector,
                              intentional_scroll_selectors=intentional_scroll_selectors,
                              intentional_vertical_scroll_selectors=intentional_vertical_scroll_selectors)
    viewport = evidence["viewport"]
    destination = artifact_directory(task)
    stem = f'{viewport["width"]}x{viewport["height"]}-{label}'
    image_path, json_path = destination / (stem + ".png"), destination / (stem + ".json")
    if image_path.exists() or json_path.exists():
        raise FileExistsError(f"Layout artifact already exists: {stem}; use a new task/label or QA run")
    page.screenshot(path=str(image_path), full_page=full_page)
    evidence.update({"task": task, "label": label, "role": role,
                     "route": urlsplit(page.url).path, "dataset": dataset,
                     "screenshot": image_path.name, "collectionIsUiPass": False})
    json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def assert_layout_contained(evidence: dict) -> None:
    """Assertions remain separate so collectors can preserve evidence of defects."""
    assert evidence["cards"], "No layout target measured; check selector/data readiness"
    assert evidence["documentWidth"] <= evidence["viewport"]["width"] + 1, (
        f'Page overflow: {evidence["documentWidth"]} > {evidence["viewport"]["width"]}'
    )
    assert evidence["viewportOutsideCount"] == 0, (
        f'{evidence["viewportOutsideCount"]} elements outside viewport without approved scrolling: '
        + json.dumps(evidence["viewportOutside"], ensure_ascii=False)[:1800]
    )
    assert evidence["cardViolationCount"] == 0, (
        f'{evidence["cardViolationCount"]} card clipping/overlap violations: '
        + json.dumps([c for c in evidence["cards"] if c["violationCount"]], ensure_ascii=False)[:1800]
    )
