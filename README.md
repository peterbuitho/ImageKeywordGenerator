# Keyword genrator for images
## Using Vision LLM
### An experiment in vibe coding using VS Code for Insiders

### Requirements

- Local LLM's running in Ollama
- OpenAI or Google API

### Release 0.1.0

#### Features

- Supported installed Ollama local vision LLM's
- Option to use OpenAI or Google AI API
- Keywords in 3 optional languages: English, Danish and Vietnamese
- Keywords are saved in json files for each language
- Support embedding keywords to image file from the generated json
- Embedding to only selected image files

![Screenshot](images/Screenshot.jpg?raw=true)

#### Known issues

- Vietnamese embedding looks wrong. Probably codepage error.
- Response from LLM's don't always have the correct format 

#### ToDo's

- Added support for LM-Studio
- Add place name lookup from image GPS data if any and vice versa
- Maybe normalize Vietnamese embedding 
