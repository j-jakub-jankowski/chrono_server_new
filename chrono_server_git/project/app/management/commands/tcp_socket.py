from django.core.management.base import BaseCommand
from app.tcp_socket.server import start_server

class Command(BaseCommand):
    help = "Starts the CHRONO TCP server"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting CHRONO socket server..."))
        start_server()
