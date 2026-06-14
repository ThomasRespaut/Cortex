import re
from function_calling import execute_tool
from model_loader import build_local_prompt, load_local_cortex_model

class TinyCortex:
    def __init__(self, model_path="./tinyllama_cortex_finetuned", adapter_path="./tinyllama_cortex_finetuned_v3_lora"):
        """
        Initialise le modèle fine-tuné et le tokenizer.
        """
        self.tokenizer, self.model, active_model, self.device = load_local_cortex_model(
            base_model=model_path,
            adapter=adapter_path,
        )
        print(f"Modèle TinyCortex chargé: {active_model}")

    def generate_response(self, prompt):
        """
        Génère une réponse en utilisant le modèle fine-tuné TinyCortex.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=96,
            num_return_sequences=1,
            do_sample=False,
            repetition_penalty=1.08,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        match = re.search(r"Réponse :(.*)", response)
        if match:
            result = match.group(1).strip()
            response = result
        print("Réponse : " + response)

        return response

    def interactive_mode(self):
        """
        Lance une interface utilisateur interactive pour poser des questions au modèle.
        """
        print("\nAssistant basé sur TinyCortex. Tapez 'stop' pour quitter.\n")
        while True:
            user_query = input("Votre question : ")
            user_question = build_local_prompt(user_query)
            if user_query.lower() == "stop":
                print("Assistant arrêté. À bientôt !")
                break
            else:
                response = self.generate_response(user_question)
                print(execute_tool(response))

# Exemple d'utilisation de la classe TinyCortex
if __name__ == "__main__":
    assistant = TinyCortex()
    assistant.interactive_mode()
