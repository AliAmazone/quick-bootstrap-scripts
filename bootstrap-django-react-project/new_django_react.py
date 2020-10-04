import os
import json
import subprocess
from argparse import ArgumentParser


def main():
    parser = ArgumentParser()
    parser.add_argument("project_name")
    args = parser.parse_args()

    n = 9

    print(f"\nStep 1/{n}: Creating project directory")
    if args.project_name in os.listdir():
        proceed = input(f"Directory \"{args.project_name}\" already exists. Continue? [y/N] ").strip().lower()
        if proceed != "y":
            return 1
    else:
        if not (args.project_name.startswith(".") and args.project_name.endswith(".")):
            os.mkdir(args.project_name)

    subprocess.run(f"copy .\\resources\\.gitignore .\\{args.project_name}\\.gitignore", shell=True)
    subprocess.run(f"copy .\\resources\\package.json .\\{args.project_name}\\package.json", shell=True)
    subprocess.run(f"copy .\\resources\\webpack.common.js .\\{args.project_name}\\webpack.common.js", shell=True)
    subprocess.run(f"copy .\\resources\\webpack.dev.js .\\{args.project_name}\\webpack.dev.js", shell=True)
    subprocess.run(f"copy .\\resources\\webpack.prod.js .\\{args.project_name}\\webpack.prod.js", shell=True)
    os.chdir(args.project_name)

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
        "pipenv install django django-heroku django-webpack-loader python-dotenv djangorestframework djangorestframework-jwt django-filter",
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

    settings[debug_line] = "DEBUG = os.environ.get('DEBUG')\n"
    settings.insert(debug_line + 1, "\n")
    settings.insert(debug_line + 2, "DEBUG_PROPAGATE_EXCEPTIONS = DEBUG\n")

    for i, line in enumerate(settings):
        if "ALLOWED_HOSTS" in line:
            hosts_line = i

    settings[hosts_line] = "ALLOWED_HOSTS = ['localhost', '.herokuapp.com']\n"

    for i, line in enumerate(settings):
        if "INSTALLED_APPS" in line:
            apps_line = i

    settings.insert(apps_line + 1, "    'backend.apps.BackendConfig',\n")
    settings.insert(apps_line + 2, "    'frontend.apps.FrontendConfig',\n")

    for i, line in enumerate(settings):
        if "DATABASES" in line:
            database_line = i

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

    settings[tz_line] = "TIME_ZONE = 'Asia/Manila'\n"

    for i, line in enumerate(settings):
        if "STATIC_URL" in line:
            static_line = i

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

    os.chdir("../..")
    subprocess.run(
        f"copy .\\resources\\urls.py .\\{args.project_name}\\frontend\\urls.py",
        shell=True
    )
    subprocess.run(
        f"copy .\\resources\\views.py .\\{args.project_name}\\frontend\\views.py",
        shell=True
    )

    print(f"\nStep 8/{n}: Configuring React directory structure")
    os.chdir(f"./{args.project_name}")
    os.makedirs("./frontend/templates/frontend", exist_ok=True)
    os.makedirs("./frontend/static/frontend/js", exist_ok=True)
    os.makedirs("./frontend/static/frontend/js/components", exist_ok=True)
    os.makedirs("./frontend/static/frontend/bundles", exist_ok=True)
    os.chdir("..")
    subprocess.run(
        f"copy .\\resources\\index.html .\\{args.project_name}\\frontend\\templates\\frontend\\index.html",
        shell=True
    )
    subprocess.run(
        f"copy .\\resources\\index.js .\\{args.project_name}\\frontend\\static\\frontend\\js\\index.js",
        shell=True
    )
    subprocess.run(
        f"copy .\\resources\\index.scss .\\{args.project_name}\\frontend\\static\\frontend\\js\\index.scss",
        shell=True
    )
    subprocess.run(
        f"copy .\\resources\\App.js .\\{args.project_name}\\frontend\\static\\frontend\\js\\components\\App.js",
        shell=True
    )

    print(f"\nStep 9/{n}: Creating environment variables")
    os.chdir(f"./{args.project_name}")
    envs = [
        f"SECRET_KEY={secret_key}\n",
        "DEBUG=1\n",
        "PYTHON_ENV=development\n",
        "\n",
    ]
    with open(".env", "w") as f:
        f.writelines(envs)

    print(f"\nThe project {args.project_name} has been initialized!")
    return 0


if __name__ == "__main__":
    main()
