import azure.functions as func
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as Exceptions
from azure.storage.blob import BlobServiceClient

from logging import getLogger
import os, uuid

logging = getLogger(__name__)

COSMOS_ACCOUNT_URI = os.environ['COSMOS_ACCOUNT_URI']
COSMOS_ACCOUNT_KEY = os.environ['COSMOS_ACCOUNT_KEY']
COSMOS_DATABASE_NAME = 'shrkmn-doc'
COSMOS_CONTAINER_NAME = 'shrkmn-doc'
BLOB_CONTAINER_NAME = 'shrkmn-doc-container'

blob_connection_string = os.getenv("AzureWebJobsStorage")
storage_access_key = os.getenv("AZURE_STORAGE_ACCESS_KEY")

app = func.FunctionApp()

@app.function_name(name="shrkmn_doc_func")
@app.queue_trigger(arg_name="azqueue", queue_name="shrkmn-doc-queue",
                               connection="AzureWebJobsStorage") 
def shrkmn_doc_func(azqueue: func.QueueMessage):
    #QueueのメッセージにBlobドキュメント名が格納される
    blob_doc_name = azqueue.get_body().decode('utf-8')
    logging.info('blob_doc_name: %s', blob_doc_name)
    
    #Blobドキュメントの内容を取得する
    try:
        logging.info('get document content of blob storage.')
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string,storage_access_key)
        blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_doc_name)
        downloader = blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
        blob_text = downloader.readall()
        logging.info('blob_text: %s', blob_text)

    except Exception as ex:
        logging.error('Exception: %s', ex)

    #CosmosDBに登録する
    #CosmosDBClientを作成
    client = cosmos_client.CosmosClient(COSMOS_ACCOUNT_URI, {'masterKey': COSMOS_ACCOUNT_KEY}, user_agent="AssistantApp", user_agent_overwrite=True)

    try:
        logging.info('create item for cosmosdb.')
        #CosmosDBに登録するitemを定義
        #idにはuuidを設定
        item = {
            "id": str(uuid.uuid4()),
            "content": blob_text
        }
        logging.info('item: %s', item)
        
        #CosmosDBのデータベースを取得
        database = client.get_database_client(COSMOS_DATABASE_NAME)
        #CosmosDBのコンテナーを取得
        container = database.get_container_client(COSMOS_CONTAINER_NAME)

        #CosmosDBに登録する
        container.create_item(body=item)
    
    except Exceptions.CosmosHttpResponseError as e:
        logging.error('CosmosHttpResponseError: %s', e.message)
    
    logging.info('finish function.')