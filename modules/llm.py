import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Specifica il checkpoint del modello scelto
checkpoint = "HuggingFaceTB/SmolLM-360M-Instruct"

# Imposta il device: usa "cuda" se hai una GPU, altrimenti "cpu"
device = "cuda" if torch.cuda.is_available() else "cpu"

# Carica il tokenizer e il modello
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForCausalLM.from_pretrained(checkpoint).to(device)

# Se usi la pipeline su GPU, specifica device=0, altrimenti -1 per la CPU
gen_device = 0 if device == "cuda" else -1
generator = pipeline(
    "text-generation", 
    model=model, 
    tokenizer=tokenizer, 
    device=gen_device
)

def generate_text(prompt, max_new_tokens=500, temperature=0.7, top_p=0.95):
    output = generator(
        prompt, 
        num_return_sequences=1, 
        max_new_tokens=max_new_tokens, 
        temperature=temperature, 
        top_p=top_p,
        do_sample=True
    )
    return output[0]['generated_text']

