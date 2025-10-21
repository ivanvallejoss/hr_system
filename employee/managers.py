""" 
Custom managers y querysets para Employee app
"""
from django.db import models;
from django.db.models import F, Q, Count, Avg, Sum, Max, Min;
from django.db.models.functions import TruncMonth, TruncYear;
from datetime import date, timedelta;

class SalaryHistoryQuerySet(models.QuerySet):
    """ 
    QuerySet custom para SalaryHistory
    Permite encadenar queries y agregar metodos de filtros.
    """

    def raises_only(self):
        """Filtra solo aumentos (no reducciones)"""
        return self.filter(new_salary__gt=F('old_salary'))
    
    def decreases_only(self):
        """Filtra solo reducciones"""
        return self.filter(new_salary__lt=F('old_salary'))
    
    def by_date_range(self, start_date=None, end_date=None):
        """Filtra por rango de fechas"""
        qs = self
        if start_date:
            qs = qs.filter(effective_date__gte=start_date)
        if end_date:
            qs = qs.filter(effective_date__lte=end_date)
        
        return qs
    
    def by_year(self, year):
        """Filtra por year especifico"""
        return self.filter(effective_date__year=year)
    
    def top_increases(self, limit=10):
        """Retorna los aumentos mas grandes"""
        return self.raises_only().order_by(
            F('new_salary') - F('old_salary')
        ).reverse()[:limit]
    
    def with_change_stats(self):
        """Agrega estadisticas de cambio"""
        return self.annotate(
            change_amount=F('new_salary') - F('old_salary'),
            change_percentage=(
                (F('new_salary') - F('old_salary')) / F('old_salary') * 100
            )
        )
    

class SalaryHistoryManager(models.Manager):
    """ 
    Manager custom para SalaryHistory
    Punto de entrada para queries
    """

    def get_queryset(self):
        """Retorna el QuerySet custom"""
        return SalaryHistoryQuerySet(self.model, using=self._db)
    
    # Exponer metodos del queryset en el manager
    def raises_only(self):
        return self.get_queryset().raises_only()
    
    def decreases_only(self):
        return self.get_queryset().decreases_only()
    
    def by_date_range(self, start_date=None, end_date=None):
        return self.get_queryset().by_date_range(start_date, end_date)
    
    def by_year(self, year):
        return self.get_queryset().by_year(year)
    
    def top_increases(self, limit=10):
        return self.get_queryset().top_increases(limit)
    
    def with_change_stats(self):
        return self.get_queryset().with_change_stats()
    
    # Analytics methods (mas complejos)
    def by_month(self, year=None):
        """Agrupa por mes con estadisticas"""
        qs = self.get_queryset()

        if year:
            qs = qs.by_year(year)

        return qs.annotate(
            month=TruncMonth('effective_date')
        ).values('month').annotate(
            count=Count('id'),
            avg_increase=Avg(F('new_salary') - F('old_salary')),
            total_increase=Sum(F('new_salary') - F('old_salary'))
        ).order_by('month')
    
    def avg_growth_by_role(self):
        """Crecimiento promedio por rol"""
        return self.select_related('employee__role').values(
            'employee__role__title'
        ).annotate(
            avg_increase_amount=Avg(F('new_salary') - F('old_salary')),
            total_changes=Count('id'),
            avg_old_salary=Avg('old_salary'),
            avg_new_salary=Avg('new_salary'),
        ).order_by('-avg_increase_amount')
    


class RoleHistoryQuerySet(models.QuerySet):
    """Queryset custom para RoleHistory"""

    def promotions_only(self):
        """Filtra solo promociones de seniority"""
        return self.filter(
            Q(old_seniority='JUNIOR', new_seniority__in=['MID', 'SENIOR']) |
            Q(old_seniority='MID', new_seniority='SENIOR')
        )
    
    def demotions_only(self):
        """Filtra solo reducciones de seniority"""
        return self.filter(
            Q(old_seniority='SENIOR', new_seniority__in=['MID', 'JUNIOR']) |
            Q(old_seniority='MID', new_seniority='JUNIOR')
        )
    
    def lateral_moves_only(self):
        """Filtra solo cambios laterales (mismo seniority)"""
        return self.filter(old_seniority=F('new_seniority')).exclude(
            old_role=F('new_role')
        )
    
    def by_date_range(self, start_date=None, end_date=None):
        """Filtra por rango de fechas"""
        qs = self
        if start_date:
            qs = qs.filter(effective_date__gte=start_date)
        if end_date:
            qs = qs.filter(effective_date__lte=end_date)
        return qs
    
    def by_year(self, year):
        """Filtra por year"""
        return self.filter(effective_date__year=year)
    

class RoleHistoryManager(models.Manager):
    """Manager custom para RoleHistory"""

    def get_query_set(self):
        return RoleHistoryQuerySet(self.model, using=self._db)
    
    def promotions_only(self):
        return self.get_query_set().promotions_only()
    
    def demotions_only(self):
        return self.get_query_set().demotions_only()
    
    def lateral_moves_only(self):
        return self.get_query_set().lateral_moves_only()
    
    def by_date_range(self, start_date=None, end_date=None):
        return self.get_query_set().by_date_range(start_date, end_date)
    
    def by_year(self, year):
        return self.get_query_set().by_year(year)
    
    def by_month(self, year=None):
        """Agrupa por mes"""
        qs = self.get_query_set()

        if year:
            qs = qs.by_year(year)

        return qs.annotate(
            month=TruncMonth('effective_date')
        ).values('month').annotate(
            total_changes=Count('id'),
            promotions=Count('id', filter=Q(
                old_seniority='JUNIOR', new_seniority__in=['MID', 'SENIOR']
            ) | Q(
                old_seniority='MID', new_seniority='SENIOR'
            ))
        ).order_by('month')
    


class EmployeeQuerySet(models.QuerySet):
    """QuerySet custom para Employee (opcional, para queries complejas)"""
    def without_recent_raises(self, months=12):
        """Empleados sin aumento en X meses"""
        from employee.models import SalaryHistory;

        cutoff_date = date.today() - timedelta(days=months * 30)

        # Empleados con ultimo aumento antes del cutoff
        with_old_raises = self.annotate(
            last_raise_date=Max('salary_history__effective_date')
        ).filter(
            last_raise_date__lt=cutoff_date
        )

        # Empleados sin ningun aumento
        without_raises = self.filter(
            salary_history__isnull=True
        )

        return with_old_raises | without_raises
    
    def active(self):
        """Solo empleados activos"""
        return self.filter(termination_date__isnull=True)
    
    def by_department(self, department_name):
        """Filtra por department"""
        return self.filter(role__department__name=department_name)