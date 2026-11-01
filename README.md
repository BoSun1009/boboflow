# boboflow

Local dependency maps and interactive workflow diagrams, with file-and-line references you can inspect.

boboflow turns Python, JavaScript, and TypeScript imports into browsable module maps. It also renders authored JSON diagrams for explaining business workflows. The Python CLI uses only the standard library and produces self-contained HTML that you can open in a browser.

## What it does

| Mode | Input | Result |
| --- | --- | --- |
| **Scan a project** | A local source directory | A grouped overview and detailed module dependency map, with source references and a scan report |
| **Render a diagram** | A JSON graph | An interactive architecture or workflow diagram; authored layouts add explicit positioning, routed edges, and layout checks |

- Search nodes, inspect details and evidence, and explore related modules or steps.
- Browse authored workflows with zoom, pan, a minimap, directed path queries, and category filters.
- Choose light or dark themes. Authored workflows also offer Classic, Signal, Blueprint, and Editorial styles.
- Use **Signal Flow** for short animations along connections and a focus ring around the selected node. Motion respects the system's reduced-motion preference.
- Switch authored workflows between English and Chinese using supplied translations.
- Export SVG; authored workflows also provide browser-based PNG, JPEG, WebP, share-card, and clipboard options.

Scanning finds static import relationships. Business workflows are supplied as JSON; they are not automatically inferred from application behavior. Animations illustrate the diagram and do not execute a workflow.

## Requirements

- **Python 3.9 or newer** on macOS or Linux. File handling uses POSIX flags; native Windows is not currently supported.
- A modern browser to view the generated HTML.
- Git to clone this repository, or download the repository as a ZIP.

No Python packages, Node.js installation, build step, API key, or running web server are required for normal use.

## Quick start

```sh
git clone https://github.com/BoSun1009/boboflow.git
cd boboflow
```

### Render the included example

```sh
python3 scripts/project_map.py render examples/business-workflow.json --out ../boboflow-demo
```

Open `../boboflow-demo/diagram.html` in your browser. The example contains a two-step review workflow. Its labels are Chinese; the authored workflow interface defaults to English. Diagram text without an English translation keeps its original wording.

Every output directory must be new. For another run, choose a different `--out` path.

### Scan your project

Replace the input path with the project you want to inspect:

```sh
python3 scripts/project_map.py scan /absolute/path/to/your-project --out ../boboflow-project-map
```

The output directory must also be **outside the scanned project**. Open `overview.html` for a grouped view, then `diagram.html` for individual modules and import references. Check `scan-report.json` for errors, skipped entries, unresolved imports, and truncation.

Arrows point from the importing file to the imported module. The module-map interface is currently Chinese; the English/Chinese switch is available in authored workflow mode.

## Create your own workflow

Start with [the example JSON](examples/business-workflow.json) and follow the [graph format reference](references/format.md) (Chinese). Render your file with:

```sh
python3 scripts/project_map.py render /absolute/path/to/workflow.json --out ../my-workflow-diagram
```

Graphs contain a `version`, `kind`, `title`, `nodes`, and `edges`. Node IDs must be unique, and edges must reference existing nodes. Evidence entries use relative file paths and positive line numbers. Relationships can be marked `observed`, `inferred`, or `manual`.

For an authored workflow, set `layout.mode` to `"authored"` and provide node positions and edge routes. The renderer checks node overlaps, bounds, edge endpoints, orthogonal routes, and routes through unrelated nodes. It also checks text placement in both languages and reports line crossings for review. These checks do not replace visual inspection in a browser.

Supply translations through `translations.en`, mapping original strings to English. Translation is explicit; no translation service is called.

## Generated files

| File | Available in | Purpose |
| --- | --- | --- |
| `diagram.html` | All modes | Self-contained interactive diagram |
| `diagram.json` | All modes | Graph data you can inspect, edit, and render again |
| `receipt.json` | All modes | Node/edge counts, HTML SHA-256, and generation metadata |
| `overview.html` | Project scans | Dependency map grouped by source directory |
| `scan-report.json` | Project scans | Scan counts, exclusions, errors, and limitations |
| `diagram-{en,zh}-{light,dark}.svg` | Authored layouts | Four language/theme variants generated without browser export |
| `layout-checks.json` | Authored layouts | Layout results for both languages, including line crossings |

## Scope and privacy

The scanner reads source files without importing or executing the target project. The CLI and generated viewers do not make network requests or include telemetry. If you use an AI assistant to inspect source or generated output, the material it reads may enter that assistant's cloud context.

Default scanning limits are **512 KiB per file**, **1,500 source files**, and **20 MiB total input**. Hidden paths, sensitive filenames, and common dependency, build, data, and log directories are excluded. Directory traversal skips symbolic links. Filename filters cannot detect every secret embedded in ordinary source; generated names and relationships can also reveal private project information.

Python imports are extracted with the standard-library AST parser, including conditional and type-checking imports. JavaScript/TypeScript imports and `export … from` statements use a heuristic matcher. Alias configuration, dynamic imports, and CommonJS `require()` are not resolved. External packages and other unresolved references are counted in the scan report rather than drawn as resolved modules.

A static map is not a runtime call graph, a security audit, or proof that a change will affect every reachable node. Authored diagrams do not synchronize with a CRM or execute business actions.

Browser image encoding, clipboard access, and media export depend on browser support and permissions. Automated DOM checks use mocks for some browser APIs and do not prove real export behavior across browsers.

## Development

Run the Python test suite from the repository root:

```sh
python3 -m unittest discover -s tests
```

Optional DOM checks live in `tests/*.cjs`. They require Node.js, `jsdom`, and the expected generated HTML fixtures; several target a larger demo that is not included here. They are not needed to run the CLI.

| Directory | Contents |
| --- | --- |
| `scripts/` | Scanning, validation, layout, localization, and HTML generation |
| `assets/` | Browser viewers, exploration tools, and Signal Flow animation |
| `examples/` | A small authored workflow |
| `references/` | Graph schema and feature documentation |
| `tests/` | Python tests and DOM checks |

[SKILL.md](SKILL.md) contains the instructions for using boboflow as an AI-assistant skill. The CLI can also be used directly as shown above.

## License

This repository does not currently include a `LICENSE` file.
