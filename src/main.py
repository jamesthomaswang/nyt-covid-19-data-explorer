import os


def main():
    input("Are you ready? Press enter for me to spin up a Streamlit server.")
    print("Setting working directory to this project's directory:")
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    print("Starting Streamlit server:")
    os.system("streamlit run src/controller.py ")


if __name__ == "__main__":
    main()
