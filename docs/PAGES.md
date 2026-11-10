# Publish the project page

Live page: [Project](https://oliverdou776.github.io/Exact-Temporal-Range-Queries-through-Local-State-Windows/). GitHub Pages is enabled; subsequent updates to `main` rebuild this page automatically.

The buildless project page is `docs/index.html`. Its styles and interaction code are in `docs/project/`; the paper PDF and figures are in `docs/assets/`, and the browser-session recordings in `docs/demos/`. The page works beneath a GitHub repository subpath and needs no package installation or build workflow.

The active publishing configuration can be checked in repository settings:

1. Open [Settings → Pages](https://github.com/OliverDOU776/Exact-Temporal-Range-Queries-through-Local-State-Windows/settings/pages).
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/docs**, then choose **Save**.
4. Wait for GitHub's Pages build to finish and use the live URL shown by GitHub.

The `.nojekyll` file serves the HTML, CSS, JavaScript and figures as static files. Subsequent updates to `main` are published by GitHub Pages automatically. This guide does not require a personal access token or a custom Actions workflow.

The teaser's budget picker displays five exact BIG001 envelopes computed by the repository solver. The query tool (`docs/demo/` and the page's “Try an exact query” section) runs a JavaScript port of the LocalWindows solver in the browser; the Python and native C++ code provide the full functionality.
