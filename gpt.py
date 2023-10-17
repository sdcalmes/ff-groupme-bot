import g4f


class GPT:

    def __init__(self):
        self.model = "gpt-3.5-turbo"

    def chat_completion(self, prompt):
        messages = [{
            "role": "user",
            "content": prompt
        }]
        completion = g4f.ChatCompletion.create(model=self.model, messages=messages)
        return completion
