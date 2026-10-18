import pytest

@pytest.fixture(scope="session")
def operator_qa_backend(isolated_backend):
    return isolated_backend

@pytest.fixture
def operator_ui(browser_instance, operator_qa_backend):
    contexts, errors = [], []
    def page_for():
        context = browser_instance.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        def forward(route):
            path = route.request.url.split("/api/v1", 1)[1]
            response = route.fetch(url=operator_qa_backend+"/api/v1"+path)
            route.fulfill(response=response)
        page.route("**/api/v1/**", forward)
        page.on("pageerror", lambda e: errors.append(str(e)))
        contexts.append(context)
        return page
    yield page_for, operator_qa_backend
    for context in contexts:
        for page in context.pages:
            # Closing a page cancels background requests; suppress only callbacks left during teardown.
            page.unroute_all(behavior="ignoreErrors")
        context.close()
    assert not errors
