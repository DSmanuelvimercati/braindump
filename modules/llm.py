import torch
from transformers import AutoTokenizer, pipeline

model_id = "google/gemma-3-1b-it"
device = "cuda" if torch.cuda.is_available() else "cpu"
gen_device = 0 if device == "cuda" else -1

tokenizer = AutoTokenizer.from_pretrained(model_id)
generator = pipeline(
    "text-generation",
    model=model_id,
    tokenizer=tokenizer,
    device=gen_device,
    torch_dtype=torch.bfloat16
)

def generate_text(prompt, max_new_tokens=1024, temperature=0.7, top_p=0.95):
    """
    Converte il prompt in formato chat, lo passa alla pipeline Gemma 3 e restituisce
    il contenuto dell'ultimo messaggio dell'assistente.
    """
    messages = [
        [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
    ]
    
    output = generator(
        messages,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        do_sample=True
    )
    
    # Assume che output[0]['generated_text'] sia una lista di messaggi
    return output[0][0]['generated_text'][-1]['content']
