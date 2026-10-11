# DSL provenance and compatibility

Use a real export as the schema baseline. Record alongside the DSL:

- Original export file and source app type.
- Dify deployment release or upstream commit, DSL `version` as exported, and export date.
- Whether the export represents a draft or a published workflow version.
- Required plugin identifiers/versions, models, tool credentials, dataset remapping, and environment variable names.
- Target deployment/version, import result, and preview/published-run results.

If a template is written without a target export, label it an unverified draft. Do not invent a DSL version or claim compatibility based only on a YAML parser. Read that release's importer and relevant node definitions when a field is unclear; preserve unknown fields unless their removal is justified.

At research commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`, [api/constants/dsl_version.py](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/constants/dsl_version.py) declares app DSL `0.7.0`. [api/services/dsl_version.py](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/services/dsl_version.py) returns a pending status for newer imported versions, and the [app importer](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/services/app_dsl_service.py) handles that status. This is evidence about that source snapshot only; do not stamp `0.7.0` into an unrelated deployment's DSL.

The [Cloud app management page](https://docs.dify.ai/en/cloud/use-dify/workspace/app-management) describes Cloud's continuously updated DSL behavior. The [self-host page](https://docs.dify.ai/en/self-host/use-dify/workspace/app-management) warns that newer DSL files may need a platform upgrade. Import into the actual target and respect its warnings; Cloud behavior is not a guarantee for a pinned self-host release.

Exported app definitions carry graph configuration and knowledge connections, not knowledge content, third-party tool API keys, logs, or analytics. Secret-type environment variables may be included if selected during export: inspect and redact the artifact before committing. Treat literal headers, prompts, Code nodes, and HTTP Request nodes as possible secret locations too.

For the new native Agent, skills and files must be shared and added separately from its DSL. Review [Build an Agent](https://docs.dify.ai/en/cloud/use-dify/build/new-agent/build) for the target edition.

Use Dify Studio's export/import interface, or an officially documented `difyctl` release supported by the target. [CLI app reference](https://docs.dify.ai/en/cli/reference/apps) distinguishes draft exports for Workflow/Chatflow from published execution and offers version-specific export options; check the installed CLI's help before using them. The public app Service API executes apps; do not fabricate an app-authoring or DSL-import endpoint for it. Console endpoints found in source are private implementation details unless independently documented.

Acceptance evidence must say what actually happened: local schema check, target import, missing-dependency resolution, preview run, publish, and published API run are distinct stages. Publishing or overwriting a shared app changes external state; stay within the user's requested action.
