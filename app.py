import sys
from os import walk, path
import csv
import argparse
from flask import Flask, redirect, url_for, request, render_template, send_file, make_response

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.route('/tagger')
def tagger():
    if app.config["HEAD"] >= len(app.config["FILES"]):
        return redirect(url_for('bye'))
    
    directory = app.config['IMAGES']
    image = app.config["FILES"][app.config["HEAD"]]
    labels = app.config["LABELS"]
    
    not_end = not(app.config["HEAD"] == len(app.config["FILES"]) - 1)
    not_start = app.config["HEAD"] > 0
    
    return render_template('tagger.html', not_end=not_end, not_start=not_start, directory=directory, image=image, labels=labels, head=app.config["HEAD"] + 1, len=len(app.config["FILES"]))

@app.route('/previous')
def previous_image():
    if app.config["HEAD"] > 0:
        update_csv()  # Save current labels before moving to the previous image
        app.config["HEAD"] -= 1
        load_labels_for_image()  # Load labels for the previous image
    return redirect(url_for('tagger'))

@app.route('/next')
def next_image():
    if app.config["HEAD"] < len(app.config["FILES"]) - 1:
        update_csv()  # Update the CSV file with current labels
        app.config["HEAD"] += 1
        load_labels_for_image()  # Load labels for the next image
    return redirect(url_for('tagger'))

@app.route("/save")
def save():
    update_csv()  # Save the current labels to the CSV file
    return "Annotations saved."

@app.route("/download_csv")
def download_csv():
    """Generate a CSV file for the current image's annotations and serve it for download."""
    image = app.config["FILES"][app.config["HEAD"]]
    labels = app.config["LABELS"]
    
    # Generate CSV content
    csv_content = "image,id,name,xMin,xMax,yMin,yMax,color\n"
    for label in labels:
        csv_content += f"{image},{label['id']},{label['name']},{label['xMin']},{label['xMax']},{label['yMin']},{label['yMax']},{label['color']}\n"
    
    # Create a response object to serve the CSV file
    response = make_response(csv_content)
    response.headers["Content-Disposition"] = f"attachment; filename={image}_annotations.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/bye")
def bye():
    return send_file("taf.gif", mimetype='image/gif')

@app.route('/add/<id>')
def add(id):
    xMin = request.args.get("xMin")
    xMax = request.args.get("xMax")
    yMin = request.args.get("yMin")
    yMax = request.args.get("yMax")
    color = request.args.get("color", "#000000")  # Default to black if no color is provided
    name = request.args.get("name", "Unnamed")    # Default to 'Unnamed' if no name is provided

    if color is None or color == "":
        color = "#000000"  # Default to black if color is missing

    if name is None or name == "":
        name = "Unnamed"  # Default to 'Unnamed' if name is missing

    app.config["LABELS"].append({
        "id": id,
        "name": name,
        "xMin": xMin,
        "xMax": xMax,
        "yMin": yMin,
        "yMax": yMax,
        "color": color
    })
    return redirect(url_for('tagger'))

@app.route('/remove/<id>')
def remove(id):
    try:
        index = int(id) - 1
        del app.config["LABELS"][index]
        for label in app.config["LABELS"][index:]:
            label["id"] = str(int(label["id"]) - 1)
        return redirect(url_for('tagger'))
    except ValueError:
        return "Invalid ID", 400

@app.route('/label/<id>')
def label(id):
    name = request.args.get("name")
    color = request.args.get("color")
    print(f"Received name: {name}, color: {color}")  # Debugging
    if color:
        app.config["LABELS"][int(id) - 1]["color"] = color
    if name:  # Update the name only if it is provided
        app.config["LABELS"][int(id) - 1]["name"] = name
    return redirect(url_for('tagger'))


@app.route('/image/<f>')
def images(f):
    images = app.config['IMAGES']
    return send_file(images + f)

def update_csv():
    """Update the CSV file with the current state of labels."""
    image = app.config["FILES"][app.config["HEAD"]]
    # Read all existing data
    rows = []
    try:
        with open(app.config["OUT"], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only keep rows that are not for the current image
                if row['image'] != image:
                    rows.append(row)
    except FileNotFoundError:
        pass  # If the CSV file doesn't exist, proceed

    # Add the current labels to the list
    for label in app.config["LABELS"]:
        print(f"Saving label: {label}")  # Add this line for debugging
        rows.append({
            'image': image,
            'id': label['id'],
            'name': label['name'],
            'xMin': label['xMin'],
            'xMax': label['xMax'],
            'yMin': label['yMin'],
            'yMax': label['yMax'],
            'color': label['color']
        })

    # Write all rows back to the CSV file
    with open(app.config["OUT"], 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["image", "id", "name", "xMin", "xMax", "yMin", "yMax", "color"])
        writer.writeheader()
        writer.writerows(rows)

def load_labels_for_image():
    """Load the labels from the CSV file for the current image."""
    image = app.config["FILES"][app.config["HEAD"]]
    app.config["LABELS"] = []
    try:
        with open(app.config["OUT"], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['image'] == image:
                    app.config["LABELS"].append({
                        'id': row['id'],
                        'name': row['name'],
                        'xMin': row['xMin'],
                        'xMax': row['xMax'],
                        'yMin': row['yMin'],
                        'yMax': row['yMax'],
                        'color': row['color']
                    })
    except FileNotFoundError:
        pass  # If the CSV file doesn't exist, simply do nothing

def load_all_labels():
    """Load all labels from the CSV file into a dictionary."""
    all_labels = {}
    try:
        with open(app.config["OUT"], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                image = row['image']
                if image not in all_labels:
                    all_labels[image] = []
                all_labels[image].append({
                    'id': row['id'],
                    'name': row['name'],
                    'xMin': row['xMin'],
                    'xMax': row['xMax'],
                    'yMin': row['yMin'],
                    'yMax': row['yMax'],
                    'color': row['color']
                })
    except FileNotFoundError:
        pass  # If the CSV file doesn't exist, return an empty dictionary
    return all_labels

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', type=str, help='specify the images directory')
    args = parser.parse_args()
    directory = args.dir
    if directory[-1] != "/":
         directory += "/"
    app.config["IMAGES"] = directory
    app.config["LABELS"] = []
    files = None
    for (dirpath, dirnames, filenames) in walk(app.config["IMAGES"]):
        files = filenames
        break
    if files is None:
        print("No files")
        sys.exit()
    app.config["FILES"] = files
    app.config["HEAD"] = 0
    
    # Automatically determine the CSV file path
    app.config["OUT"] = path.join(directory, "annotations.csv")
    print(files)

    # Load existing labels if the CSV file exists
    if path.exists(app.config["OUT"]):
        all_labels = load_all_labels()
        for i, file in enumerate(files):
            if file in all_labels:
                app.config["LABELS"] = all_labels[file]  # Load labels for the first image
                app.config["HEAD"] = i  # Start from the image that has labels
                break
    else:
        # If the CSV doesn't exist, create a new one with the header
        with open(app.config["OUT"], 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["image", "id", "name", "xMin", "xMax", "yMin", "yMax", "color"])
            writer.writeheader()

    load_labels_for_image()  # Load labels for the first image (if available)
    app.run(debug=True)