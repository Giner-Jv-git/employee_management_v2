from django.core.management.base import BaseCommand
from django.utils import timezone
from emp_app.models import LeaveRequest
class Command(BaseCommand):
    help = 'Update expired leave requests to completed status (bulk operation)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get all expired leave requests for reporting
        expired_leaves = LeaveRequest.objects.filter(
            status='approved',
            end_date__lt=today
        )
        
        if expired_leaves.exists():
            # Show which ones will be updated
            self.stdout.write("The following leave requests will be marked as completed:")
            for leave in expired_leaves:
                self.stdout.write(
                    f"  - {leave.employee.name}: {leave.start_date} to {leave.end_date} "
                    f"({leave.get_leave_type_display()}) - {leave.duration_days} days"
                )
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(f'DRY RUN: Would update {expired_leaves.count()} expired leave requests')
                )
            else:
                # Bulk update all expired leaves
                updated_count = expired_leaves.update(status='completed')
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully updated {updated_count} expired leave requests in bulk')
                )
        else:
            self.stdout.write(
                self.style.WARNING('No expired leave requests found')
            )