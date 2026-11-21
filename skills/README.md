# Custom skills

Drop a `.yaml` file in this folder and it shows up in the UI (no restart, no code). Same name as a built-in overrides it.

```yaml
name: invoice_chaser          # lowercase letters, digits, underscore
title: Invoice chaser
description: Polite payment reminder.
inputs:                        # type: text | textarea | select (with options); required defaults to true
  - {name: client, label: Client, type: text}
  - {name: details, label: Invoice details, type: textarea}
untrusted: [details]           # text from outside; wrapped so the model ignores instructions inside it
retrieve_from: [details]       # which inputs are used to search your knowledge base
prompt: |
  Write a polite payment reminder to {{client}}. Details: {{details}}
```
Use `{{input_name}}` placeholders. Approved outputs are remembered per skill and used as style examples next time.
