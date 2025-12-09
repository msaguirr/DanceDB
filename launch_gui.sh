
#!/bin/zsh
# Launch Copperknob Import GUI with correct venv and path
if [ -f "$PWD/venv/bin/activate" ]; then
	source "$PWD/venv/bin/activate"
else
	echo "venv not found! Exiting."
	exit 1
fi

# Prefer run_copperknob_gui.py if it exists, else fallback to src/copperknob_import_gui.py
if [ -f "$PWD/run_copperknob_gui.py" ]; then
	python run_copperknob_gui.py
elif [ -f "$PWD/src/copperknob_import_gui.py" ]; then
	python src/copperknob_import_gui.py
else
	echo "No GUI entry point found!"
	exit 1
fi
