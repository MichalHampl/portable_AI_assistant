from llama_cpp import Llama
import random, string

model = "llm\llm_models\dolphin-2.6-mistral-7b-dpo-laser.Q5_K_S.gguf"
#model = "llm\llm_models\Meta-Llama-3-8B-Instruct-Q5_K_M.gguf"
llm = Llama(model_path=model,  n_gpu_layers=-1, n_ctx=2048, n_batch=521, verbose=True, seed=random.randint(-32000,32000))

def text_to_text(prompt, tokens):
    llm.set_seed(random.randint(-32000,32000))
    output = llm("Q:" + prompt + "A: ", max_tokens=tokens, stop=["Q:"], echo=False)
    #print(output["choices"][0]["text"])
    return output["choices"][0]["text"]

def ttt_generator(prompt, token_len):
    tokens = llm.tokenize(str(prompt).encode("utf-8"))
    
    gen = llm.generate(tokens)
    for tkn in gen:
        yield llm.detokenize([tkn]).decode("utf-8")

#generator function for text to text
def ttt_generator2(prompt, token_len):
    llm.set_seed(random.randint(-32000,32000))
    output = llm("Q:" + prompt + "A: ", max_tokens=token_len, stop=["Q:"], echo=False,stream=True)
    for tkn in output:
        yield tkn["choices"][0]["text"]
        

#i = 0
#for text in ttt_generator2("How do i cook potatoes",512):
#    i = i+1
#    print(text,end="\n")
#print("\n",i)