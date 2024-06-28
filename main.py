from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
import logging

from starlette.websockets import WebSocketDisconnect

load_dotenv()

app = FastAPI()

websockets = []
channel = None


class Order(BaseModel):
    clientId: str
    deliveryNeeded: bool
    completionDate: str
    completionTime: str
    price: float


class OrderDetail(BaseModel):
    orderId: str
    productId: str
    quantity: int


class SensorData(BaseModel):
    sensorId: str
    temperature: float
    humidity: float
    timestamp: str


@app.get("/orders")
async def read_orders():
    try:
        response = httpx.get('http://localhost:8080/orders')
        logging.info(f"Data-api response status: {response.status_code}, text: {response.text}")
        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders")
async def create_order(order: Order, background_tasks: BackgroundTasks):
    try:

        order_data = str(order.dict())
        print(order_data)

        response = httpx.post('http://localhost:8080/orders', json=order.dict())
        logging.info(f"Data-api response status: {response.status_code}, text: {response.text}")

        print(response.status_code)
        if response.status_code == 201:

            logging.info("Notifying WebSocket clients")
            for websocket in websockets:
                await websocket.send_text("Refetch orders")

            return response.json()

        else:
            raise HTTPException(status_code=500, detail="Failed to create order in data-api")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notification/sensor-alert")
async def create_alert(sensorData: SensorData):
    try:
        sensor_name = "Unknown Sensor"
        if sensorData.sensorId == "9920ccbf-d43e-4713-bc6d-5460375f6e81":
            sensor_name = "Warehouse1 Sensor"
        elif sensorData.sensorId == "1920ccbf-d43e-4713-bc6d-5460375f6e82":
            sensor_name = "Kitchen1 Sensor"

        for websocket in websockets:
            await websocket.send_text("Alert: " + sensor_name + " has temperature: " +
                                      str(sensorData.temperature)[:2] + "°C and humidity: " +
                                      str(sensorData.humidity)[:2] + "% at " + sensorData.timestamp)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders/{order_id}/details")
async def create_order_details(order_id: str, orderDetail: OrderDetail, background_tasks: BackgroundTasks):
    try:
        response = httpx.post(f'http://localhost:8080/orders/{order_id}/details', json=orderDetail.dict())
        logging.info(f"Data-api response status: {response.status_code}, text: {response.text}")

        if response.status_code == 201:
            for websocket in websockets:
                await websocket.send_text("Refetch orders")
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Failed to create order details in data-api")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/orders/{orderId}")
async def delete_order(orderId: str):
    try:
        response = httpx.delete(f'http://localhost:8080/orders/{orderId}')

        if response.status_code == 204:
            for websocket in websockets:
                await websocket.send_text("Refetch orders")
            return response.status_code
        else:
            raise HTTPException(status_code=500, detail="Failed to delete order in data-api")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websockets.remove(websocket)
