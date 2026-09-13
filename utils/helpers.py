from llm.llm import client
import utils.printer as printer


def status():
    models = client.models.list().data
    printer.models_table(models)
