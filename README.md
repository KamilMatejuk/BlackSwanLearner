# Python Template
This is a template repository for BlackSwan python services, based on SocketIO, with integrated swagger console. To create a new repository from this template, follow [this guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

## To start server:
```
echo 'PORT=8000' > .env.local
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload
```

## To use SwaggerUI
* update [openapi.yaml](openapi.yaml) based on [documentation](https://swagger.io/specification/)
* open http://127.0.0.1:8000/swagger-ui/
