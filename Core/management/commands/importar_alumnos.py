import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from Core.models import Alumno  # Asegúrate de usar el nombre correcto de tu app

class Command(BaseCommand):
    help = 'Importa alumnos desde un archivo CSV'

    def handle(self, *args, **kwargs):
        with open('Alumnos corregido.csv', newline='', encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            total = 0

            for row in reader:
                fecha_raw = row.get('Fecha Nacimiento', '').strip()
                if fecha_raw:
                    try:
                        fecha_nacimiento = datetime.strptime(fecha_raw, '%d-%m-%Y').date()
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Formato inválido en fila: {row}"))
                        continue
                else:
                    fecha_nacimiento = None

                Alumno.objects.create(
                    rut=row['Rut'],
                    nombre=row['Nombre'],
                    correo_personal=row['Correo Personal'],
                    correo_inacap=row['Correo Inacap'],
                    celular=row['Celular'],
                    fecha_nacimiento=fecha_nacimiento
                )
                total += 1

            self.stdout.write(self.style.SUCCESS(f'Se importaron {total} alumnos.'))
