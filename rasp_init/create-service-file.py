from os.path import join, isfile
import argparse


template = """\
[Unit]
Description=Inhalator Service

[Service]
ExecStart={python3_executable} {main_path}
WorkingDirectory={main_dir}
Environment=DISPLAY={display}
Environment=XAUTHORITY={xauthority}
Restart=always
Type=simple
User=pi

[Install]
WantedBy=default.target
"""


def generate(output_file, python):
    main_dir = "/home/pi/Inhalator"
    main_path = join(main_dir, "main.py")
    if not isfile(main_path):
        raise FileNotFoundError(main_path)

    contents = template.format(
        main_path=main_path,
        python3_executable="/home/pi/Inhalator/.inhalator_env/bin/python3",
        main_dir=main_dir,
        xauthority="/home/pi/.Xauthority",
        display=":0"
    )
    with open(output_file, "w") as f:
        f.write(contents)

    print("Created service file at %s:" % output_file)
    print()
    print(contents)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_file", "-o",
        help="The path of the generated service file")
    parser.add_argument(
        "--python", "-p",
        help="The name/path of the python interpreter that will be used to start the service",
        default="/usr/bin/env python3")
    args = parser.parse_args()

    generate(output_file=args.output_file, python=args.python)
