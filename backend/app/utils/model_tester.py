from volcenginesdkarkruntime import Ark


# For more information，please check this document（https://www.volcengine.com/docs/82379/1263279）
client = Ark(api_key='d5ef8378-b9b6-4c76-98ee-c55ebda4954d')


print("----- multimodal embeddings request -----")
resp = client.multimodal_embeddings.create(
    model="doubao-embedding-vision-250615",
    input=[
        {
            "text":"标题: Clone the ultralytics repository git clone https://github.com/ultralytics/ultralytics # Navigate to the cloned directory cd ultralytics # Install the package in editable mode for development pip install -e .",
            "type":"text"
        },
        {
            "text":"标题: Clone the ultralytics repository git clone https://github.com/ultralytics/ultralytics # Navigate to the cloned directory cd ultralytics # Install the package in editable mode for development pip install -e .",
            "type":"text"
        }
    ]
)
print(resp)
print(resp.data.embedding)