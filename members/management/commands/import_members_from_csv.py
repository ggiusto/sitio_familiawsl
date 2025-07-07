import csv
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import transaction # Para asegurar la integridad de la base de datos

class Command(BaseCommand):
    help = 'Imports members from a CSV file into the members.Member model, handling relationships by original CSV IDs.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import.')
        parser.add_argument(
            '--model',
            type=str,
            default='members.Member',
            help='The Django app_label.ModelName to import data into (e.g., members.Member).'
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='The delimiter used in the CSV file (default: ",").'
        )
        parser.add_argument(
            '--header_row',
            type=int,
            default=1,
            help='The 1-based row number of the header (default: 1).'
        )
        # Note: --update_existing is less useful with ID-based import if IDs are not PKs.
        # It's kept but primarily uses 'correomail' for update logic.
        parser.add_argument(
            '--update_existing',
            action='store_true',
            help='Update existing members based on correomail (if unique) or full name match. If not set, it tries to create new ones and skips on unique constraint violations.'
        )
        parser.add_argument(
            '--create_missing_relations',
            action='store_true',
            help='Create placeholder members if a parent or spouse is referenced by ID but not found (only for direct references that exist as separate rows in the CSV with that ID).'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        model_label = options['model']
        delimiter = options['delimiter']
        header_row_index = options['header_row'] - 1
        update_existing = options['update_existing']
        create_missing_relations = options['create_missing_relations'] # This flag is tricky with ID-based, will mostly be for unresolvable IDs.

        try:
            app_label, model_name = model_label.split('.')
            model = apps.get_model(app_label, model_name)
        except ValueError:
            raise CommandError(f'Invalid model format: {model_label}. Use app_label.ModelName.')
        except LookupError:
            raise CommandError(f'Model "{model_label}" not found. Did you register it in your app?')

        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV file not found at: {csv_file_path}')

        self.stdout.write(self.style.SUCCESS(f'Attempting to import data from "{csv_file_path}" into "{model_label}"...'))
        self.stdout.write(f'Update existing members: {update_existing}')
        self.stdout.write(f'Create missing relations placeholders: {create_missing_relations}')
        self.stdout.write(self.style.WARNING(
            'Note: Relations (padre, madre, conyuge) will be processed in a second pass using original CSV IDs. '
            'Ensure all related members are present in the CSV and that `id` column is unique and correct.'
        ))

        # --- FASE 1: Crear Miembros y Mapear IDs Originales a Objetos Django ---
        # Stores {original_csv_id: django_member_object}
        original_id_to_django_obj = {}
        # Stores CSV row data for the second pass
        csv_rows_for_relations = [] 
        
        imported_count_phase1 = 0
        updated_count_phase1 = 0
        skipped_count_phase1 = 0

        self.stdout.write(self.style.HTTP_INFO('\n--- Phase 1: Creating/Updating Members (without relations) ---'))

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=delimiter)

            for _ in range(header_row_index):
                next(reader)

            header = [h.strip() for h in next(reader)]
            self.stdout.write(f'Detected headers: {header}')

            for row_num, row_data in enumerate(reader, start=header_row_index + 2):
                if not row_data or all(not cell.strip() for cell in row_data):
                    continue
                
                row_dict = dict(zip(header, (cell.strip() for cell in row_data[:len(header)])))
                csv_rows_for_relations.append((row_num, row_dict)) # Store for phase 2

                original_csv_id = row_dict.get('id')
                if not original_csv_id:
                    skipped_count_phase1 += 1
                    self.stdout.write(self.style.ERROR(
                        f'Row {row_num}: Missing "id" in CSV. Skipping member creation.'
                    ))
                    continue

                member_data = {}
                
                try:
                    # Mapeo de campos directos
                    for field_name in [
                        'first_name', 'last_name_paterno', 'last_name_materno', 'apodo',
                        'lugar_nacimiento', 'estudios', 'ocupación', 'relationship',
                        'padrino_de_bautismo', 'madrina_de_bautismo', 'correomail',
                        'phone_number', 'address', 'whatsapp', 'facebook', 'linkedin',
                        'instagram'
                    ]:
                        if field_name in row_dict and hasattr(model, field_name):
                            value = row_dict[field_name]
                            if value:
                                # Special handling for 'ocupación' - it has an accent
                                if field_name == 'ocupación':
                                    member_data['ocupacion'] = value # Map 'ocupación' to 'ocupacion' in model
                                else:
                                    member_data[field_name] = value

                    # Manejo de DateField
                    for date_field in ['birth_date', 'fallecimiento_date']:
                        if date_field in row_dict and row_dict[date_field]:
                            try:
                                member_data[date_field] = datetime.strptime(row_dict[date_field], '%Y-%m-%d').date()
                            except ValueError:
                                self.stdout.write(self.style.WARNING(
                                    f'Row {row_num}: Invalid date format for {date_field}: "{row_dict[date_field]}". Skipping this date.'
                                ))

                    # ImageField handling (just a warning)
                    if 'foto_principal' in row_dict and row_dict['foto_principal']:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping "foto_principal". ImageField import from CSV requires special handling.'
                        ))

                    # Decide if creating or updating
                    member = None
                    created = False
                    
                    # Use correomail as a unique lookup if available for updates
                    if update_existing and 'correomail' in member_data and member_data['correomail']:
                        try:
                            member, created = model.objects.update_or_create(
                                correomail=member_data['correomail'],
                                defaults=member_data
                            )
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(
                                f'Row {row_num}: Error updating/creating member by email "{member_data["correomail"]}": {e}. Attempting to create new.'
                            ))
                            member = None # Reset to try creating
                    
                    if not member: # If not updated by email, or email failed, try to create
                        try:
                            member = model.objects.create(**member_data)
                            created = True
                        except Exception as e:
                            # This catches cases like unique constraint violation on name if it were unique
                            skipped_count_phase1 += 1
                            self.stdout.write(self.style.ERROR(
                                f'Row {row_num}: Error creating member {member_data.get("first_name")} {member_data.get("last_name_paterno")}: {e}. Skipping.'
                            ))
                            continue # Skip to next row

                    if created:
                        imported_count_phase1 += 1
                        self.stdout.write(self.style.SUCCESS(f'Row {row_num}: Successfully created member: {member} (ID: {member.pk})'))
                    else:
                        updated_count_phase1 += 1
                        self.stdout.write(self.style.WARNING(f'Row {row_num}: Successfully updated member: {member} (ID: {member.pk})'))
                    
                    original_id_to_django_obj[original_csv_id] = member

                except Exception as e:
                    skipped_count_phase1 += 1
                    self.stdout.write(self.style.ERROR(f'Row {row_num}: Unexpected error during Phase 1: {e}'))

        self.stdout.write(self.style.SUCCESS('--- Phase 1 Summary ---'))
        self.stdout.write(self.style.SUCCESS(f'Created in Phase 1: {imported_count_phase1}'))
        self.stdout.write(self.style.SUCCESS(f'Updated in Phase 1: {updated_count_phase1}'))
        self.stdout.write(self.style.ERROR(f'Skipped in Phase 1: {skipped_count_phase1}'))
        
        if not original_id_to_django_obj:
            self.stdout.write(self.style.ERROR("No members were imported in Phase 1. Cannot proceed with Phase 2."))
            return

        # --- FASE 2: Establecer Relaciones ---
        relations_set_count = 0
        skipped_relations_count = 0

        self.stdout.write(self.style.HTTP_INFO('\n--- Phase 2: Establishing Relationships ---'))

        # Usamos una transacción para asegurar que las actualizaciones de relaciones sean atómicas
        with transaction.atomic():
            for row_num, row_dict in csv_rows_for_relations:
                original_csv_id = row_dict.get('id')
                if not original_csv_id or original_csv_id not in original_id_to_django_obj:
                    # Este caso ya fue manejado en la fase 1 o no se pudo crear el miembro
                    continue 

                current_member_obj = original_id_to_django_obj[original_csv_id]
                updated_fields = []

                try:
                    # Padre
                    padre_csv_id = row_dict.get('padre_id')
                    if padre_csv_id:
                        padre_obj = original_id_to_django_obj.get(padre_csv_id)
                        if padre_obj:
                            current_member_obj.padre = padre_obj
                            updated_fields.append('padre')
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'Row {row_num}: Padre with ID "{padre_csv_id}" not found in imported members. Skipping father relation for "{current_member_obj}".'
                            ))
                            skipped_relations_count += 1
                    
                    # Madre
                    madre_csv_id = row_dict.get('madre_id')
                    if madre_csv_id:
                        madre_obj = original_id_to_django_obj.get(madre_csv_id)
                        if madre_obj:
                            current_member_obj.madre = madre_obj
                            updated_fields.append('madre')
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'Row {row_num}: Madre with ID "{madre_csv_id}" not found in imported members. Skipping mother relation for "{current_member_obj}".'
                            ))
                            skipped_relations_count += 1

                    # Cónyuge
                    conyuge_csv_id = row_dict.get('conyuge_id')
                    if conyuge_csv_id:
                        conyuge_obj = original_id_to_django_obj.get(conyuge_csv_id)
                        if conyuge_obj:
                            current_member_obj.conyuge = conyuge_obj
                            updated_fields.append('conyuge')
                            # También establecer la relación inversa si el cónyuge no la tiene
                            if not conyuge_obj.conyuge: # Evitar bucles infinitos si ya está seteado o es mutuo
                                conyuge_obj.conyuge = current_member_obj
                                conyuge_obj.save(update_fields=['conyuge']) # Guardar inmediatamente para que el cambio persista
                                self.stdout.write(self.style.SUCCESS(
                                    f'Row {row_num}: Set reciprocal spouse for "{conyuge_obj}".'
                                ))
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'Row {row_num}: Conyuge with ID "{conyuge_csv_id}" not found in imported members. Skipping spouse relation for "{current_member_obj}".'
                            ))
                            skipped_relations_count += 1

                    if updated_fields:
                        current_member_obj.save(update_fields=updated_fields) # Solo guarda los campos de relación
                        relations_set_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Row {row_num}: Relations updated for "{current_member_obj}". Fields: {", ".join(updated_fields)}'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Row {row_num}: Error setting relations for "{current_member_obj}": {e}.'
                    ))
                    skipped_relations_count += 1

        self.stdout.write(self.style.SUCCESS('--- Phase 2 Summary ---'))
        self.stdout.write(self.style.SUCCESS(f'Relations successfully set for: {relations_set_count} members'))
        self.stdout.write(self.style.ERROR(f'Relations skipped: {skipped_relations_count}'))
        self.stdout.write(self.style.SUCCESS('Import process completed.'))
