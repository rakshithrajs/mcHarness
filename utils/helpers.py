from llm.llm import client


def status():
    print(client.models.list().model_dump_json(indent=2))
