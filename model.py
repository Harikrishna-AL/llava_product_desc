import argparse
import torch

from llava.constants import (
    IMAGE_TOKEN_INDEX,
    DEFAULT_IMAGE_TOKEN,
    DEFAULT_IM_START_TOKEN,
    DEFAULT_IM_END_TOKEN,
    IMAGE_PLACEHOLDER,
)
from llava.conversation import conv_templates, SeparatorStyle
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init
from llava.mm_utils import (
    process_images,
    tokenizer_image_token,
    get_model_name_from_path,
)

from PIL import Image

import requests
from PIL import Image
from io import BytesIO
import re


def image_parser(args):
    out = args.image_file.split(args.sep)
    return out


def load_image(image_file):
    if image_file.startswith("http") or image_file.startswith("https"):
        response = requests.get(image_file)
        image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        image = Image.open(image_file).convert("RGB")
    return image


# image_file="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1000&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8cHJvZHVjdHxlbnwwfHwwfHx8MA%3D%3D"

def load_images(image_files):
    out = []
    for image_file in image_files:
        image = load_image(image_file)
        out.append(image)
    return out

model_path = "liuhaotian/llava-v1.6-mistral-7b"

model_name = get_model_name_from_path(model_path)
tokenizer, model, image_processor, context_len = load_pretrained_model(
    model_path, None, get_model_name_from_path(model_path)
)
conv = conv_templates["mistral_instruct"].copy()

def eval_model(args, images, chat_mode=False):
    # Model
    disable_torch_init()

    qs = args.query
    # if with_image:
    image_token_se = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN

    
    if IMAGE_PLACEHOLDER in qs:
        if model.config.mm_use_im_start_end:
            qs = re.sub(IMAGE_PLACEHOLDER, image_token_se, qs)
        else:
            qs = re.sub(IMAGE_PLACEHOLDER, DEFAULT_IMAGE_TOKEN, qs)
    # elif IMAGE_PLACEHOLDER not in qs and chat_mode == False:
    #     if model.config.mm_use_im_start_end:
    #         qs = image_token_se + "\n" + qs
    #     else:
    #         qs = DEFAULT_IMAGE_TOKEN + "\n" + qs
    else:
        if model.config.mm_use_im_start_end:
            qs = image_token_se + "\n" + qs
        else:
            qs = DEFAULT_IMAGE_TOKEN + "\n" + qs


    if "llama-2" in model_name.lower():
        conv_mode = "llava_llama_2"
    elif "mistral" in model_name.lower():
        conv_mode = "mistral_instruct"
    elif "v1.6-34b" in model_name.lower():
        conv_mode = "chatml_direct"
    elif "v1" in model_name.lower():
        conv_mode = "llava_v1"
    elif "mpt" in model_name.lower():
        conv_mode = "mpt"
    else:
        conv_mode = "llava_v0"

    if args.conv_mode is not None and conv_mode != args.conv_mode:
        print(
            "[WARNING] the auto inferred conversation mode is {}, while `--conv-mode` is {}, using {}".format(
                conv_mode, args.conv_mode, args.conv_mode
            )
        )
    else:
        args.conv_mode = conv_mode

    
    conv.append_message(conv.roles[0], qs)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()
    # fix this lol
    # if with_image:
    # image_files = image_parser(args)
    # images = load_images(image_files)
    image_sizes = [x.size for x in images]
    # print(image_sizes)
    images_tensor = process_images(
        images,
        image_processor,
        model.config
    ).to(model.device, dtype=torch.float16)
    # print(model.config)
    if chat_mode:
        input_ids = tokenizer_image_token(prompt, tokenizer, None, return_tensors="pt").unsqueeze(0).cuda()
    
    else:
        input_ids = (
            tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
            .unsqueeze(0)
            .cuda()
        )

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            images=images_tensor,
            image_sizes=image_sizes,
            do_sample=True if args.temperature > 0 else False,
            temperature=args.temperature,
            top_p=args.top_p,
            num_beams=args.num_beams,
            max_new_tokens=args.max_new_tokens,
            use_cache=True,
        )

    outputs = tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
    # print(outputs)
    conv.append_message(conv.roles[1], outputs)
    print(conv.get_prompt())
    return outputs




def get_description(images, prompt=None):
    if prompt is None:
        prompt = """Describe the product in the image in detail in a writing stype optimium for advertisements.
        
        Write in a way where advertisement is done using excitement.
        """
    else:
        prompt = prompt
    # image_file = "https://llava-vl.github.io/static/images/view.jpg"
    # image_file="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1000&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8cHJvZHVjdHxlbnwwfHwwfHx8MA%3D%3D"
    image_file="https://in.canon/media/image/2021/09/25/30be26306419482888690cac6adb9de6_product_category_eosr3.png"
    
    args = type('Args', (), {
        "model_path": model_path,
        "model_base": None,
        "model_name": get_model_name_from_path(model_path),
        "query": prompt,
        "conv_mode": "mistral_instruct",
        "image_file": image_file,
        "sep": ",",
        "temperature": 0,
        "top_p": None,
        "num_beams": 1,
        "max_new_tokens": 512
    })()
    if prompt is None:
        out = eval_model(args, images)
    else:
        out = eval_model(args, images, chat_mode=True)
    return out


def rewrite_description(images,additional_prompt,out):
    # additional_prompt = input("Enter any additional prompts if needed: ")
    
    new_base_prompt = """Combine the new details with the output you generated earlier and rewrite the advertisement in an exciting way."""
    new_prompt = out + "\n" + "These are some additional details about that product that are required in the product description: \n" +  additional_prompt + "\n" + new_base_prompt
    image_file="https://in.canon/media/image/2021/09/25/30be26306419482888690cac6adb9de6_product_category_eosr3.png"
    new_args = type('Args', (), {
        "model_path": model_path,
        "model_base": None,
        "model_name": get_model_name_from_path(model_path),
        "query": new_prompt,
        "conv_mode": "mistral_instruct",
        "image_file": image_file,
        "sep": ",",
        "temperature": 0,
        "top_p": None,
        "num_beams": 1,
        "max_new_tokens": 512
    })()
    
    final_out = eval_model(new_args, images)

    return final_out
    
