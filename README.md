# Zendesk Response Times

Tool to evaluate response times for a Zendesk ticket.

For every customer comment, we evaluate the time taken for the next agent response.

Additionally, we observe whether the response time involved the weekends (Saturday and Sunday).

# Output

The tool (script) generates a CSV file of the following columns:

| Column | Type | Description |
| --- | --- | --- |
| email | string | Email of customer or agent |
| user type | string | `customer` or `agent` |
| commented at | string | ISO8601-formatted time when the customer or agent responded |
| formula | string | Arithmetic showing how the response time was calculated |
| weekends | string | If weekends were involved, this would print the dates of the weekends |
| response time | string | Total time taken for this response from agent (empty if customer comment) |

You can see examples under the [examples](examples) folder.

# Usage

You can run the script locally or set up on CircleCI for convenience.

You would also need to set up the following secrets via environment variables:

- `ZENDESK_EMAIL`: Zendesk user email
- `ZENDESK_TOKEN`: Zendesk user API token
- `ZENDESK_SUBDOMAIN`: Zendesk subdomain (e.g., foobar if you are on foobar.zendesk.com)

## Local

Ensure you have Python 3.10.1.

Install dependencies via poetry:

```shell
poetry install
```

To evaluate a ticket, run:

```console
$ export ZENDESK_SUBDOMAIN=foobar
$ export ZENDESK_EMAIL=<email of API token owner>
$ export ZENDESK_TOKEN=<API token value>

# generates a 123.csv (default) for your evaluation
$ poetry run python cli.py https://foobar.zendesk.com/agent/tickets/123

$ open 123.csv

$ poetry run python cli.py https://foobar.zendesk.com/agent/tickets/99 -o foobar-99.csv

$ open foobar-99.csv
```

## CircleCI

**Note**: Please set up the project on CircleCI first, and add the required secrets as [project environment variables](https://circleci.com/docs/env-vars#setting-an-environment-variable-in-a-project).

> :bulb: This is a template repository on GitHub.
> Hence, you can [create your own from this](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

You can then [trigger this via the build UI on CircleCI](https://circleci.com/docs/triggers-overview#run-a-pipeline-from-the-circleci-web-app).

1. Go to your main branch.
2. Click on **Trigger Pipeline** on the top right.
3. Add a pipeline parameter `url`, where the value is the ticket URL (e.g., https://foobar.zendesk.com/agent/tickets/123)
4. Download the csv from the Artifacts tab when done!
