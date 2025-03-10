# Keyword genrator for images
## Using Vision LLM

### Requirements

- Local LLM's running in Ollama
- OpenAI or Google API

### Features

- Support selected local Ollama vision models: Llava models, Llama3.2-vision, Llava-llama models
- Keywords in 3 optional languages: English, Danish and Vietnamese
- Keywords are saved in json files for each language
- Support embedding keywords to image file from the generated json
- Embedding to only selected image files

![Screenshot](images/Screenshot.jpg?raw=true)

### Known issues

- Vietnamese embedding looks wrong. Probably codepage error.
- Response from LLM's don't always have the correct format 

### ToDo's

- Lookup from Ollama list of models instead
- Added support for LM-Studio
- Add place name lookup from image GPS data if any and vice versa
- Maybe normalize Vietnamese embedding 
