import sys
from os import walk, path
import csv
import argparse
from flask import Flask, redirect, url_for, request, render_template, send_file, make_response

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.before_request
def log_request_info():
    print(f"Handling request: {request.method} {request.url}")
    if request.args:
        print(f"Request arguments: {request.args}")
    if request.form:
        print(f"Request form data: {request.form}")

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
    
    # Generate CSV content with the new fields
    csv_content = "image,id,name,xMin,xMax,yMin,yMax,color,type,xOffset,yOffset\n"  # Add new fields to the header
    for label in labels:
        csv_content += f"{image},{label['id']},{label['name']},{label['xMin']},{label['xMax']},{label['yMin']},{label['yMax']},{label['color']},{label['type']},{label.get('xOffset', 0)},{label.get('yOffset', 0)}\n"
    
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
    color = request.args.get("color", "#000000")
    name = request.args.get("name", "Unnamed")
    type = request.args.get("type", "box")
    xOffset = request.args.get("xOffset", 0)
    yOffset = request.args.get("yOffset", 0)

    # Log the new label being added
    print(f"Adding new label with ID: {id}, Name: {name}, Type: {type}, Coords: ({xMin},{yMin}) to ({xMax},{yMax}), Color: {color}, xOffset: {xOffset}, yOffset: {yOffset}")

    app.config["LABELS"].append({
        "id": id,
        "name": name,
        "xMin": xMin,
        "xMax": xMax,
        "yMin": yMin,
        "yMax": yMax,
        "color": color,
        "type": type,
        "xOffset": xOffset,
        "yOffset": yOffset
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
    xOffset = request.args.get("xOffset")
    yOffset = request.args.get("yOffset")
    xMin = request.args.get("xMin")
    xMax = request.args.get("xMax")
    yMin = request.args.get("yMin")
    yMax = request.args.get("yMax")

    print(f"Received label update: name={name}, color={color}, xOffset={xOffset}, yOffset={yOffset}, xMin={xMin}, xMax={xMax}, yMin={yMin}, yMax={yMax}")

    label = app.config["LABELS"][int(id) - 1]

    # Update label attributes
    if color:
        label["color"] = color
    if name:
        label["name"] = name
    if xOffset:
        label["xOffset"] = float(xOffset)
    if yOffset:
        label["yOffset"] = float(yOffset)
    if xMin:
        label["xMin"] = float(xMin)
    if xMax:
        label["xMax"] = float(xMax)
    if yMin:
        label["yMin"] = float(yMin)
    if yMax:
        label["yMax"] = float(yMax)

    return redirect(url_for('tagger'))

@app.route('/image/<f>')
def images(f):
    images = app.config['IMAGES']
    return send_file(images + f)

def update_csv():
    """Update the CSV file with the current state of labels."""
    image = app.config["FILES"][app.config["HEAD"]]
    print(f"Updating CSV for image: {image}")  # Log the image being updated
    
    rows = []
    try:
        with open(app.config["OUT"], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Keep rows that are not related to the current image
                if row['image'] != image:
                    rows.append(row)
    except FileNotFoundError:
        print("CSV file not found, will create a new one.")  # Log if the file doesn't exist
    
    # Append the current labels for the image
    for label in app.config["LABELS"]:
        row = {
            'image': image,
            'id': label['id'],
            'name': label['name'],
            'xMin': label['xMin'],
            'xMax': label['xMax'],
            'yMin': label['yMin'],
            'yMax': label['yMax'],
            'color': label['color'],
            'type': label.get('type', 'box'),
            'xOffset': label.get('xOffset', 0),  # New field, default to 0 if not found
            'yOffset': label.get('yOffset', 0)   # New field, default to 0 if not found
        }
        rows.append(row)
        print(f"Writing row to CSV: {row}")  # Log each row being written
    
    # Write all rows back to the CSV
    with open(app.config["OUT"], 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["image", "id", "name", "xMin", "xMax", "yMin", "yMax", "color", "type", "xOffset", "yOffset"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV update complete for image: {image}\n")  # Log completion of CSV update

def load_labels_for_image():
    """Load the labels from the CSV file for the current image."""
    image = app.config["FILES"][app.config["HEAD"]]
    app.config["LABELS"] = []  # Clear current labels
    try:
        with open(app.config["OUT"], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If the row corresponds to the current image, load the label
                if row['image'] == image:
                    app.config["LABELS"].append({
                        'id': row['id'],
                        'name': row['name'],
                        'xMin': row['xMin'],
                        'xMax': row['xMax'],
                        'yMin': row['yMin'],
                        'yMax': row['yMax'],
                        'color': row['color'],
                        'type': row.get('type', 'box'),  # Default to 'box' if type is missing
                        'xOffset': row.get('xOffset', 0),  # New field, default to 0 if not found
                        'yOffset': row.get('yOffset', 0)   # New field, default to 0 if not found
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
                    'color': row['color'],
                    'type': row.get('type', 'box'),  # Default to 'box' if type is missing
                    'xOffset': row.get('xOffset', 0),  # New field, default to 0 if not found
                    'yOffset': row.get('yOffset', 0)   # New field, default to 0 if not found
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
            writer = csv.DictWriter(f, fieldnames=["image", "id", "name", "xMin", "xMax", "yMin", "yMax", "color", "type", "xOffset", "yOffset"])
            writer.writeheader()

    load_labels_for_image()  # Load labels for the first image (if available)
    app.run(debug=True)