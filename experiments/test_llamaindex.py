import sys
import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
import os.path
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)

os.environ["OPENAI_API_KEY"] = "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"

# check if storage already exists
PERSIST_DIR = "./storage"
if not os.path.exists(PERSIST_DIR + os.sep + "docstore.json"):
    # load the documents and create the index
    documents = SimpleDirectoryReader("data").load_data()
    index = VectorStoreIndex.from_documents(documents)
    # store it for later
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    # load the existing index
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)
import sys

# from llama_index.llms.gemini import Gemini

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gemini.key"

# llm = Gemini()
input("OK to proceed?")

query_engine = index.as_query_engine()
while True:
    print(query_engine.query(input("Input next question:")))
    print("************************************************\n")
