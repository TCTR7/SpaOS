// Source-level regression tests; API, storage and React hooks are isolated.
// Run: node --test frontend/tests/ux-review.test.cjs
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const root = path.resolve(__dirname, "..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const compile = source => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React },
}).outputText;
function callback(file, name, context) {
  const source = ts.createSourceFile(file, read(file), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let expression;
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(source) === name) {
      expression = ts.isCallExpression(node.initializer) ? node.initializer.arguments[0] : node.initializer;
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  assert.ok(expression, `Missing source callback ${name}`);
  return vm.runInNewContext(compile(`const target = ${expression.getText(source)}; target;`), context);
}
function load(file, imports, globals = {}) {
  const module = { exports: {} };
  vm.runInNewContext(compile(read(file)), { module, exports: module.exports, require: imports, ...globals });
  return module.exports;
}
const noop = () => {};
function hooks() {
  let active;
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
    Fragment: "Fragment",
    useState: initial => {
      const owner = active, i = owner.si++;
      if (owner.first) owner.states[i] = initial;
      return [owner.states[i], value => { owner.states[i] = value; }];
    },
    useRef: initial => {
      const i = active.ri++;
      if (active.first) active.refs[i] = { current: initial };
      return active.refs[i];
    },
    useEffect: effect => { if (active.first) active.effects.push(effect); },
  };
  const instance = () => ({ si: 0, ri: 0, first: true, states: [], refs: [], effects: [] });
  function render(owner, fn) { active = owner; owner.si = owner.ri = 0; const result = fn(); owner.first = false; return result; }
  return { react, instance, render };
}

test("CRM opens the linked customer once, then respects a different search", async () => {
  let rows = [], selected, opens = 0, lookups = 0;
  const context = {
    URLSearchParams, window: { location: { search: "?customer_id=A" } },
    customerRequest: { current: 0 }, nextOffset: null, listQuery: { current: "" }, selectedId: { current: null },
    setLoading: noop, setMoreLoading: noop, setNextOffset: noop, setError: noop,
    setCustomers: value => { rows = typeof value === "function" ? value(rows) : value; },
    fetchCustomerPage: async () => ({ items: [{ id: "B" }], nextOffset: null }),
    apiRequest: async () => { lookups++; return { id: "A" }; },
    selectCustomer: value => { selected = value; context.selectedId.current = value?.id; },
    detail: { open: () => opens++ },
  };
  const loadCustomers = callback("src/app/(admin)/admin/customers/page.tsx", "loadCustomers", context);
  await loadCustomers("", false, "A");
  assert.equal(selected.id, "A"); assert.equal(opens, 1); assert.equal(lookups, 1);
  await loadCustomers("B");
  assert.equal(selected.id, "B"); assert.equal(opens, 1); assert.equal(lookups, 1);
  assert.deepEqual(Array.from(rows, row => row.id), ["B"]);
});

for (const status of [409, 503]) test(`Manual booking: retry stays on same ID; a new form gets a new ID after ${status}`, async () => {
  const h = hooks(), owner = h.instance(), storage = new Map(), sent = [];
  class ApiError extends Error { constructor(status, message) { super(message); this.status = status; } }
  let nextId = 0;
  const { useManualBatch } = load("src/lib/use-manual-batch.ts", id => id === "react" ? h.react : id.includes("branch-guard") ? { useBranchGuard: noop } : {
    ApiError,
    createManualBatch: async body => { sent.push({ ...body }); throw new ApiError(status, "Rejected or uncertain"); },
    fetchManualBatch: async () => { throw new ApiError(404, "Không có lần tạo lịch đã lưu với mã này"); },
  }, {
    crypto: { randomUUID: () => `00000000-0000-4000-8000-${String(++nextId).padStart(12, "0")}` },
    sessionStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
    window: { dispatchEvent: noop }, Event: class {},
  });
  const render = () => h.render(owner, () => useManualBatch("scope", noop, noop));
  let batch = render(); owner.effects.forEach(effect => effect()); batch = render();
  await batch.submit({ customer_id: "A" }); batch = render();
  if (status === 503) { await batch.check(); batch = render(); }
  assert.equal(batch.uncertain, false);
  await batch.submit({ customer_id: "A", note: "edited retry" }); batch = render();
  assert.equal(sent[0].request_id, sent[1].request_id);
  if (status === 503) { await batch.check(); batch = render(); }
  // Execute the actual page callback rather than manually calling defer here.
  const context = new Proxy({ referencesReady: true, manualUncertain: batch.uncertain, manualBatch: batch,
    user: { role: "ADMIN" }, selectedDate: "2026-10-29", createEmptySessionRow: () => ({}) }, {
    has: () => true, get: (target, key) => key in target ? target[key] : noop,
  });
  callback("src/app/(admin)/admin/bookings/page.tsx", "openCreateModal", context)();
  batch = render(); await batch.submit({ customer_id: "B" }); batch = render();
  assert.notEqual(sent[0].request_id, sent[2].request_id);
  if (status === 503) {
    const entries = JSON.parse(storage.get("scope:queue"));
    assert.equal(entries.length, 2);
    assert.equal(entries.find(entry => entry.id === sent[0].request_id).body.customer_id, "A");
    assert.equal(entries.find(entry => entry.id === sent[2].request_id).body.customer_id, "B");
  }
});

for (const role of ["ADMIN", "CUSTOMER"]) test(`${role} help library does not open a second tour dialog`, () => {
  const h = hooks(), shell = h.instance(), library = h.instance(), listeners = new Set();
  const currentPath = role === "ADMIN" ? "/admin/help" : "/branch/help";
  const storage = new Map([[`spaos_tour_${role}_user`, "active"]]);
  const guides = load("src/lib/screen-guides.ts", noop);
  const { ScreenHelp } = load("src/components/screen-help.tsx", id => id === "react" ? h.react :
    id.includes("spa-navigation") ? { usePathname: () => currentPath, useRouter: () => ({ push: noop }) } :
    id.includes("screen-guides") ? guides : id.includes("branch-guard") ? { assertAdminNavigationSafe: noop } :
    id.includes("button") ? { Button: "Button" } : { Modal: "Modal" }, {
    localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
    window: { addEventListener: (_, fn) => listeners.add(fn), removeEventListener: (_, fn) => listeners.delete(fn) },
  });
  const render = (owner, isLibrary) => h.render(owner, () => ScreenHelp({ role, identity: "user", slug: "branch", library: isLibrary }));
  const modal = tree => tree.children.find(child => child?.type === "Modal");
  render(shell, false); render(library, true);
  shell.effects.forEach(effect => effect()); library.effects.forEach(effect => effect());
  assert.equal(listeners.size, 1);
  // Customer help is a library page without a tour step of its own.
  const hasCurrentGuide = role === "ADMIN";
  assert.equal(modal(render(shell, false)).props.open, hasCurrentGuide);
  assert.equal(modal(render(library, true)).props.open, false);
  modal(render(shell, false)).props.onClose();
  assert.equal(modal(render(shell, false)).props.open, false);
  assert.equal(modal(render(library, true)).props.open, false);
  listeners.forEach(start => start());
  assert.equal(modal(render(shell, false)).props.open, hasCurrentGuide);
  assert.equal(modal(render(library, true)).props.open, false);
});
