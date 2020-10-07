import os
import json
import subprocess
from warnings import warn
from argparse import ArgumentParser
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESOURCES_DIR = BASE_DIR / "resources"

def main():
    parser = ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("-l", "--location", default=None)
    args = parser.parse_args()

    n = 10

    print(f"\nStep 1/{n}: Creating project directory")

    if "-" in args.project_name:
        warn("project_name contains invalid characters '-'; automatically replacing with '_'")
        args.project_name = args.project_name.replace("-", "_")

    if args.location is None:
        args.location = BASE_DIR / args.project_name
    else:
        args.location = Path(args.location).resolve()

    if args.location.exists():
        proceed = input(f"Directory \"{args.project_name}\" already exists. Continue? [y/N] ").strip().lower()
        if proceed != "y":
            return 0
    else:
        os.makedirs(args.location, exist_ok=True)

    resources = [
        '.gitignore',
        'package.json',
        'webpack.common.js',
        'webpack.dev.js',
        'webpack.prod.js',
    ]

    for resource in resources:
        subprocess.run(f"copy {RESOURCES_DIR / resource} {args.location / resource}", shell=True)

    os.chdir(args.location)

    with open("package.json", "r") as f:
        package = json.load(f)

    package["name"] = args.project_name

    with open("package.json", "w") as f:
        json.dump(package, f, indent=2)

    print(f"\nStep 2/{n}: Initializing git repository")
    subprocess.run("git init", shell=True)

    print(f"\nStep 3/{n}: Installing Python deps")
    subprocess.run(
        "pipenv --python 3.7",
        shell=True,
    )
    subprocess.run(
        "pipenv install django django-heroku django-webpack-loader python-dotenv djangorestframework djangorestframework-jwt django-filter gunicorn",
        shell=True,
    )

    print(f"\nStep 4/{n}: Installing Node.js deps")
    subprocess.run(
        "npm install -D",
        shell=True,
    )

    print(f"\nStep 5/{n}: Setting up Django project")
    subprocess.run(
        f"pipenv run django-admin startproject {args.project_name} .",
        shell=True,
    )
    subprocess.run(
        f"pipenv run python manage.py startapp backend",
        shell=True,
    )
    subprocess.run(
        f"pipenv run python manage.py startapp frontend",
        shell=True,
    )

    print(f"\nStep 6/{n}: Configuring Django settings")
    os.chdir(args.project_name)
    with open("settings.py", "r") as f:
        settings = f.readlines()

    for i, line in enumerate(settings):
        if "from pathlib" in line:
            import_line = i
            break

    settings.insert(import_line + 1, "\n")
    settings.insert(import_line + 2, "load_dotenv()\n")
    settings.insert(import_line, "from dotenv import load_dotenv\n")
    settings.insert(import_line, "import os\n")

    for i, line in enumerate(settings):
        if "SECRET_KEY" in line:
            key_line = i
            break

    secret_key = settings[key_line].split(" = ")[1].strip()[1:-1]
    settings[key_line] = "SECRET_KEY = os.environ.get('SECRET_KEY')\n"

    for i, line in enumerate(settings):
        if "DEBUG" in line:
            debug_line = i
            break

    settings[debug_line] = "DEBUG = os.environ.get('DEBUG')\n"
    settings.insert(debug_line + 1, "\n")
    settings.insert(debug_line + 2, "DEBUG_PROPAGATE_EXCEPTIONS = DEBUG\n")

    for i, line in enumerate(settings):
        if "ALLOWED_HOSTS" in line:
            hosts_line = i
            break

    settings[hosts_line] = "ALLOWED_HOSTS = ['localhost', '.herokuapp.com']\n"

    for i, line in enumerate(settings):
        if "INSTALLED_APPS" in line:
            apps_line = i
            break

    settings.insert(apps_line + 1, "    'backend.apps.BackendConfig',\n")
    settings.insert(apps_line + 2, "    'frontend.apps.FrontendConfig',\n")
    settings.insert(apps_line + 3, "    'webpack_loader',\n")
    settings.insert(apps_line + 4, "    'django_filters',\n")
    settings.insert(apps_line + 5, "    'rest_framework',\n")

    for i, line in enumerate(settings):
        if "DATABASES" in line:
            database_line = i
            break

    rest_config = [
        "\n",
        "# REST API\n",
        "\n",
        "REST_FRAMEWORK = {\n",
        "    'DEFAULT_FILTER_BACKENDS': [\n",
        "        'django_filters.rest_framework.DjangoFilterBackend',\n",
        "    ],\n",
        "}\n",
        "\n",
    ]
    set_split1, set_split2 = settings[:database_line], settings[database_line:]
    set_split1.extend(rest_config)
    set_split1.extend(set_split2)
    settings = set_split1

    for i, line in enumerate(settings):
        if "TIME_ZONE" in line:
            tz_line = i
            break

    settings[tz_line] = "TIME_ZONE = 'Asia/Manila'\n"

    for i, line in enumerate(settings):
        if "STATIC_URL" in line:
            static_line = i
            break

    webpack_config = [
        "\n",
        "WEBPACK_LOADER = {\n",
        "    'DEFAULT': {\n",
        "        'CACHE': False,\n",
        "        'BUNDLE_DIR_NAME': 'frontend/bundles/',\n",
        "        'STATS_FILE': BASE_DIR / 'webpack-stats.json',\n",
        "    },\n",
        "}\n",
        "\n",
    ]
    set_split1, set_split2 = settings[:static_line], settings[static_line:]
    set_split1.extend(webpack_config)
    set_split1.extend(set_split2)
    settings = set_split1

    env_config = [
        "\n",
        "PYTHON_ENV = os.environ.get('PYTHON_ENV')\n",
        "\n",
        "if PYTHON_ENV == 'production':\n",
        "    import django_heroku\n",
        "    django_heroku.settings(locals())\n",
        "\n",
    ]
    settings.extend(env_config)

    with open("settings.py", "w") as f:
        f.writelines(settings)

    print(f"\nStep 7/{n}: Configuring URL patterns")
    with open("urls.py", "r") as f:
        urls = f.readlines()

    for i, line in enumerate(urls):
        if "from django.urls" in line:
            import_line = i

    urls[import_line] = "from django.urls import include, path\n"

    for i, line in enumerate(urls):
        if "admin/" in line:
            admin_line = i

    # urls.insert(admin_line + 1, "    path('api/', include('backend.urls')),\n")
    urls.insert(admin_line + 1, "    path('', include('frontend.urls')),\n")

    with open("urls.py", "w") as f:
        f.writelines(urls)

    os.chdir(BASE_DIR)
    subprocess.run(
        f"copy {RESOURCES_DIR / 'urls.py'} {args.location / 'frontend/urls.py'}",
        shell=True
    )
    subprocess.run(
        f"copy {RESOURCES_DIR / 'views.py'} {args.location / 'frontend/views.py'}",
        shell=True
    )

    print(f"\nStep 8/{n}: Configuring React directory structure")
    os.chdir(args.location)
    os.makedirs("./frontend/templates/frontend", exist_ok=True)
    os.makedirs("./frontend/static/frontend/js/components", exist_ok=True)
    os.makedirs("./frontend/static/frontend/bundles", exist_ok=True)
    os.chdir(BASE_DIR)
    subprocess.run(
        f"copy {RESOURCES_DIR / 'index.html'} {args.location / 'frontend/templates/frontend/index.html'}",
        shell=True
    )
    subprocess.run(
        f"copy {RESOURCES_DIR / 'index.js'} {args.location / 'frontend/static/frontend/js/index.js'}",
        shell=True
    )
    subprocess.run(
        f"copy {RESOURCES_DIR / 'index.scss'} {args.location / 'frontend/static/frontend/js/index.scss'}",
        shell=True
    )
    subprocess.run(
        f"copy {RESOURCES_DIR / 'App.js'} {args.location / 'frontend/static/frontend/js/components/App.js'}",
        shell=True
    )

    print(f"\nStep 9/{n}: Creating environment variables")
    os.chdir(args.location)
    envs = [
        f"SECRET_KEY={secret_key}\n",
        "DEBUG=1\n",
        "PYTHON_ENV=development\n",
        "\n",
    ]
    with open(".env", "w") as f:
        f.writelines(envs)

    print(f"\nStep 10/{n}: Creating initial commit")
    subprocess.run("git add .", shell=True)
    subprocess.run("git commit -m \"Bootstrap Django-React project\"", shell=True)

    print(f"\nThe project {args.project_name} has been initialized!")
    return 0


if __name__ == "__main__":
    main()
