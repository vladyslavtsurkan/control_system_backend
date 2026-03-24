import ssl
import asyncio
import aio_pika


async def main():
    ORG_UUID = "019d11f2-8c24-773d-82b5-18617285dbbb"  # Replace with your UUID

    # 1. Configure mTLS Context
    ssl_context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH, cafile="infra/rabbitmq/certs/ca_certificate.pem"
    )
    ssl_context.load_cert_chain(
        certfile=f"infra/rabbitmq/certs/collector_{ORG_UUID}_certificate.pem",
        keyfile=f"infra/rabbitmq/certs/collector_{ORG_UUID}_key.pem",
    )

    # 2. Connect via AMQPS
    connection = await aio_pika.connect_robust("amqps://0.0.0.0:5671/", ssl_context=ssl_context)

    print(f"✅ Successfully connected to RabbitMQ as {ORG_UUID}!")
    await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
