import requests
import openpyxl
from tempfile import NamedTemporaryFile

API_URL = "http://127.0.0.1:8006/add/excel/business/products"
BRIEF_ID = 1


def create_test_excel():
    wb = openpyxl.Workbook()
    ws = wb.active

    # header
    ws.append(["name", "description", "price"])

    # test data
    ws.append(["iPhone 15", "Latest Apple smartphone", 1200])
    ws.append(["Samsung TV", "4K Smart Television", 800])
    ws.append(["MacBook Pro", "Apple laptop M3", 2500])

    tmp = NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    return tmp.name


def send_excel(file_path):
    with open(file_path, "rb") as f:
        files = {
            "file": (
                "products.xlsx",
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        data = {
            "brief_id": BRIEF_ID
        }

        response = requests.post(API_URL, files=files, data=data)

        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)


if __name__ == "__main__":
    excel_file = create_test_excel()
    print(f"Created test Excel file at: {excel_file}")
    send_excel(excel_file)
