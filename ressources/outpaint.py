# https://github.com/Woolverine94/biniou
# outpaint.py
import gradio as gr
import os
import PIL
import cv2
import numpy as np
import torch
from diffusers import StableDiffusionInpaintPipeline
from compel import Compel
import time
import random
from ressources.scheduler import *
from ressources.common import *
from ressources.gfpgan import *
import tomesd

device_outpaint = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Gestion des modèles
model_path_outpaint = "./models/inpaint/"
model_path_safety_checker = "./models/Stable_Diffusion/"
os.makedirs(model_path_outpaint, exist_ok=True)
os.makedirs(model_path_safety_checker, exist_ok=True)
model_list_outpaint = []

for filename in os.listdir(model_path_outpaint):
    f = os.path.join(model_path_outpaint, filename)
    if os.path.isfile(f) and (filename.endswith('.ckpt') or filename.endswith('.safetensors')):
        model_list_outpaint.append(f)

model_list_outpaint_builtin = [
    "Uminosachi/realisticVisionV30_v30VAE-inpainting",
    "runwayml/stable-diffusion-inpainting",
]

for k in range(len(model_list_outpaint_builtin)):
    model_list_outpaint.append(model_list_outpaint_builtin[k])

# Bouton Cancel
stop_outpaint = False

def initiate_stop_outpaint() :
    global stop_outpaint
    stop_outpaint = True

def check_outpaint(step, timestep, latents) : 
    global stop_outpaint
    if stop_outpaint == False :
        return
    elif stop_outpaint == True :
        stop_outpaint = False
        try:
            del ressources.outpaint.pipe_outpaint
        except NameError as e:
            raise Exception("Interrupting ...")
    return

def prepare_outpaint(img_outpaint, top, bottom, left, right) :
#     image = cv2.imread(img_outpaint) 
    image = np.array(img_outpaint)
    mask = np.zeros((image.shape[0], image.shape[1], 3), dtype = np.uint8)
    top = int(top)
    bottom = int(bottom)
    left = int(left)
    right = int(right)
    image = cv2.copyMakeBorder(
        image, 
        top, 
        bottom, 
        left, 
        right, 
        cv2.BORDER_CONSTANT, 
        None, 
        [255, 255, 255]
    )
    mask = cv2.copyMakeBorder(
        mask, 
        top, 
        bottom, 
        left, 
        right, 
        cv2.BORDER_CONSTANT, 
        None, 
        [255, 255, 255]
    )
#    timestamp = time.time()
#    savename_image = f".tmp/{timestamp}_image.png"
#    savename_mask = f".tmp/{timestamp}_mask.png"
#    cv2.imwrite(savename_image, image) 
#    cv2.imwrite(savename_mask, mask) 
    return image, image, mask, mask



def image_outpaint(
    modelid_outpaint, 
    sampler_outpaint, 
    img_outpaint, 
    mask_outpaint, 
    rotation_img_outpaint, 
    prompt_outpaint, 
    negative_prompt_outpaint, 
    num_images_per_prompt_outpaint, 
    num_prompt_outpaint, 
    guidance_scale_outpaint,
    denoising_strength_outpaint, 
    num_inference_step_outpaint, 
    height_outpaint, 
    width_outpaint, 
    seed_outpaint, 
    use_gfpgan_outpaint, 
    nsfw_filter, 
    tkme_outpaint,
    progress_outpaint=gr.Progress(track_tqdm=True)
    ):
    
    nsfw_filter_final, feat_ex = safety_checker_sd(model_path_safety_checker, device_outpaint, nsfw_filter)

    if modelid_outpaint[0:9] == "./models/" :
        pipe_outpaint = StableDiffusionInpaintPipeline.from_single_file(
            modelid_outpaint, 
            torch_dtype=torch.float32, 
            use_safetensors=True, 
            safety_checker=nsfw_filter_final, 
            feature_extractor=feat_ex
        )
    else :        
        pipe_outpaint = StableDiffusionInpaintPipeline.from_pretrained(
            modelid_outpaint, 
            cache_dir=model_path_outpaint, 
            torch_dtype=torch.float32, 
            use_safetensors=True, 
            safety_checker=nsfw_filter_final, 
            feature_extractor=feat_ex,
            resume_download=True,
            local_files_only=True if offline_test() else None
        )

    pipe_outpaint = get_scheduler(pipe=pipe_outpaint, scheduler=sampler_outpaint)
    pipe_outpaint = pipe_outpaint.to(device_outpaint)
    pipe_outpaint.enable_attention_slicing("max")
    tomesd.apply_patch(pipe_outpaint, ratio=tkme_outpaint)
    
    if seed_outpaint == 0:
        random_seed = random.randrange(0, 10000000000, 1)
        final_seed = random_seed
    else:
        final_seed = seed_outpaint
    generator = []
    for k in range(num_prompt_outpaint):
        generator.append([torch.Generator(device_outpaint).manual_seed(final_seed + (k*num_images_per_prompt_outpaint) + l ) for l in range(num_images_per_prompt_outpaint)])

#   angle_outpaint = 360 - rotation_img_outpaint   
#   img_outpaint["image"] = img_outpaint["image"].rotate(angle_outpaint, expand=True)
#   dim_size = correct_size(width_outpaint, height_outpaint, 512)
#   image_input = img_outpaint["image"].convert("RGB")
#   mask_image_input = img_outpaint["mask"].convert("RGB")
#   image_input = image_input.resize((dim_size[0],dim_size[1]))
#   mask_image_input = mask_image_input.resize((dim_size[0],dim_size[1]))    
#   savename = f"outputs/mask.png"
#   mask_image_input.save(savename)    


    image_input = img_outpaint.convert("RGB")
    mask_image_input = mask_outpaint.convert("RGB")
    dim_size = round_size(image_input)
    savename_mask = f"outputs/mask.png"
    mask_image_input.save(savename_mask) 

#    mask_image_input = PIL.Image.open(mask_outpaint)
#    mask_image_input = image_input.convert("RGB")    
    
    prompt_outpaint = str(prompt_outpaint)
    negative_prompt_outpaint = str(negative_prompt_outpaint)
    if prompt_outpaint == "None":
        prompt_outpaint = ""
    if negative_prompt_outpaint == "None":
        negative_prompt_outpaint = ""

    compel = Compel(tokenizer=pipe_outpaint.tokenizer, text_encoder=pipe_outpaint.text_encoder, truncate_long_prompts=False)
    conditioning = compel.build_conditioning_tensor(prompt_outpaint)
    neg_conditioning = compel.build_conditioning_tensor(negative_prompt_outpaint)
    [conditioning, neg_conditioning] = compel.pad_conditioning_tensors_to_same_length([conditioning, neg_conditioning])
    
    final_image = []
    
    for i in range (num_prompt_outpaint):
        image = pipe_outpaint(
            image=image_input,
            mask_image=mask_image_input,            
            prompt_embeds=conditioning,
            negative_prompt_embeds=neg_conditioning,
            num_images_per_prompt=num_images_per_prompt_outpaint,
            guidance_scale=guidance_scale_outpaint,
            strength=denoising_strength_outpaint,
            width=dim_size[0],
            height=dim_size[1],
            num_inference_steps=num_inference_step_outpaint,
            generator = generator[i],
            callback = check_outpaint,
        ).images

        for j in range(len(image)):
            timestamp = time.time()
            seed_id = random_seed + i*num_images_per_prompt_outpaint + j if (seed_outpaint == 0) else seed_outpaint + i*num_images_per_prompt_outpaint + j
            savename = f"outputs/{seed_id}_{timestamp}.png"
            if use_gfpgan_outpaint == True :
                image[j] = image_gfpgan_mini(image[j])
            image[j].save(savename)
            final_image.append(savename)

    final_image.append(savename_mask)

    del nsfw_filter_final, feat_ex, pipe_outpaint, generator, image_input, mask_image_input, image
    clean_ram()

    return final_image, final_image
