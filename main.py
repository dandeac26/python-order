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

            return {"message": "Order created successfully"}

        else:
            raise HTTPException(status_code=500, detail="Failed to create order in data-api")

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
