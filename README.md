# AGPC Prototipo
Instalar:
# pip install fastapi
# pip install uvicorn
# pip install chromadb
# pip install spacy
terminal :python -m spacy download es_core_news_sm
# pip install requests
# pip install sentence_transformers




# Comando para ejecutar : uvicorn main:app --reload

# indicaciones para hacer funcionar el proyecto 
# instalar Python 3.10, Descargar e instalar desde el siguiente enlace:
https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe 
Durante la instalación, asegurate de marcar la opción "Add Python to PATH".

# crear un entorno virtual: Instalar virtualenvwrapper (y, en algunos casos, también virtualenv)
pip install virtualenvwrapper
En algunos sistemas puede que necesites instalar también virtualenv (pip install virtualenv)
# Crear el entorno virtual con una versión específica de Python:
mkvirtualenv -p "C:\Python311\python.exe" mi_entorno311
¿Cómo encontrar la ruta de Python? where python
Ejemplo de ruta típica: C:\Users\TuUsuario\AppData\Local\Programs\Python\Python311\python.exe

# clonar el repositorio
git clone <url-del-repositorio>
cd <carpeta-del-proyecto>

# instalar las depedencias 
pip install -r requirements.txt

# Descargar Modelo de Lenguaje (Spacy)
Necesario para el procesamiento de texto en español:
python -m spacy download es_core_news_sm

# Configuración de la API Key (Importante)
Por seguridad, las claves no se suben al código. Debes configurar tu propia clave de Google Gemini localmente.

Crea un archivo nuevo en la raíz del proyecto llamado .env.

Abre el archivo y pega tu API Key con el siguiente formato (sin espacios extra ni comillas):
GEMINI_API_KEY=AIzaSy...Tu_Clave_Aqui...
Nota: Asegúrate de que el archivo .env esté incluido en tu .gitignore para no subirlo accidentalmente a GitHub.

# usar el siguiente comando para arrancar el servidor (ejecutar)
uvicorn main:app --reload
Esto levantará el servidor local con recarga automática. Abrí el navegador en http://localhost:8000.