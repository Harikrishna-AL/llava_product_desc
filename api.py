from fastapi import FastAPI, File, UploadFile
from typing import List
from PIL import Image
import requests
from translate import translate
from model import get_description, rewrite_description
import io

app = FastAPI()

@app.post("/get_desc")
async def get_desc(image: UploadFile = File(...), prompt: str = None, conv : object = None):
    image_bytes = await image.read()
    image = Image.open(io.BytesIO(image_bytes))
  
    description = get_description([image], prompt=prompt, conv=conv)
    
    return {"description": description}

@app.post("/rewrite_desc")
async def rewrite_desc(additional: str, output: str,image: UploadFile = File(...)):
    # if len(descriptions) != 2:
    #     return {"error": "Please provide two descriptions."}
    # print("additional",additional)
    # print("output",output)
    # print("image",
    image_bytes = await image.read()
    image = Image.open(io.BytesIO(image_bytes))
    
    rewritten_desc = rewrite_description(images=[image], additional_prompt=additional, out=output)
    
    return {"rewritten_description": rewritten_desc}

@app.post("/translate_desc")
async def translate_desc(description: str, lang: str):
    translated_desc = translate(description, lang)
    
    return {"translated_description": translated_desc}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19999)
