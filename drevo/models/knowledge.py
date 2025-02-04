from django.db import models
from mptt.models import TreeForeignKey
from django.urls import reverse
from users.models import User
from ..managers import ZManager
from .category import Category
from .knowledge_rating import ZnRating
from .relation_type import Tr
from .knowledge_grade_scale import KnowledgeGradeScale


class Znanie(models.Model):
    """
    Класс для описания сущности 'Знание'
    """
    title = 'Знание'
    name = models.CharField(max_length=256,
                            verbose_name='Тема',
                            unique=True
                            )
    category = TreeForeignKey(Category,
                              on_delete=models.PROTECT,
                              verbose_name='Категория',
                              null=True,
                              blank=True,
                              limit_choices_to={'is_published': True}
                              )
    tz = models.ForeignKey('Tz',
                           on_delete=models.PROTECT,
                           verbose_name='Вид знания'
                           )
    content = models.TextField(max_length=2048,
                               blank=True,
                               null=True,
                               verbose_name='Содержание'
                               )
    href = models.URLField(max_length=256,
                           verbose_name='Источник',
                           help_text='укажите www-адрес источника',
                           null=True,
                           blank=True)
    source_com = models.CharField(max_length=256,
                                  verbose_name='Комментарий к источнику',
                                  null=True,
                                  blank=True
                                  )
    author = models.ForeignKey('Author',
                               on_delete=models.PROTECT,
                               verbose_name='Автор',
                               help_text='укажите автора',
                               null=True,
                               blank=True
                               )
    date = models.DateField(auto_now_add=True,
                            verbose_name='Дата создания',
                            )
    updated_at = models.DateTimeField(auto_now=True,
                                      verbose_name='Дата и время редактирования',
                                      )
    user = models.ForeignKey(User,
                             on_delete=models.PROTECT,
                             editable=False,
                             verbose_name='Пользователь'
                             )
    order = models.IntegerField(verbose_name='Порядок',
                                help_text='укажите порядковый номер',
                                null=True,
                                blank=True
                                )

    is_published = models.BooleanField(default=False,
                                       verbose_name='Опубликовано?'
                                       )
    labels = models.ManyToManyField('Label',
                                    verbose_name='Метки',
                                    blank=True
                                    )
    # Для обработки записей (сортировка, фильтрация) вызывается собственный Manager,
    # в котором уже установлена фильтрация по is_published и сортировка
    objects = models.Manager()
    published = ZManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('zdetail', kwargs={"pk": self.pk})

    def voting(self, user, value):
        rating_obj = self.znrating_set.filter(user=user).first()

        if rating_obj:
            if value == rating_obj.value:
                rating_obj.value = ZnRating.BLANK
            else:
                rating_obj.value = value

            rating_obj.save()
        else:
            ZnRating.objects.create(znanie=self, user=user, value=value)

    def get_users_vote(self, user):
        rating_obj = self.znrating_set.filter(user=user).first()

        if rating_obj:
            if rating_obj.value in (ZnRating.LIKE, ZnRating.DISLIKE):
                return rating_obj.value

        return None

    def get_likes_count(self):
        return self.znrating_set.filter(value=ZnRating.LIKE).count()

    def get_dislikes_count(self):
        return self.znrating_set.filter(value=ZnRating.DISLIKE).count()

    def get_comments_count(self):
        return self.comments.filter(parent=None).count()

    def get_table_object(self):
        if self.tz.name != 'Таблица':
            return None

        row_type_name = 'Строка'
        col_type_name = 'Столбец'
        value_type_name = 'Значение'

        row_type = Tr.objects.get(name=row_type_name)
        col_type = Tr.objects.get(name=col_type_name)
        value_type = Tr.objects.get(name=value_type_name)

        rows = sorted(
            self.base.filter(tr=row_type).select_related('bz', 'rz'),
            key=lambda x: x.rz.order if x.rz.order else 0,
            reverse=True
        )
        cols = sorted(
            self.base.filter(tr=col_type).select_related('bz', 'rz'),
            key=lambda x: x.rz.order if x.rz.order else 0,
            reverse=True
        )
        values = self.base.filter(tr=value_type).select_related('rz')

        target_rows = rows
        target_cols = cols

        if rows[0].rz.tz.is_group:
            target_rows = rows[0].get_grouped_relations()
        if cols[0].rz.tz.is_group:
            target_cols = cols[0].get_grouped_relations()

        if not all([rows, cols, values]):
            return None

        matrix = list()

        for i, row in enumerate(target_rows):
            matrix.append([])
            for j, col in enumerate(target_cols):
                matrix[i].append(None)
                values_list = list(
                    filter(
                        lambda x: len(x.rz.base.all()) == 2 and all(
                            map(lambda y: y.rz == row.rz or y.rz ==
                                col.rz, x.rz.base.all())
                        ),
                        values
                    )
                )
                if values_list:
                    matrix[i][j] = values_list[0].rz

        table_object = {
            'rows': rows,
            'cols': cols,
            'values': matrix,
        }
        return table_object

    def get_users_grade(self, user: User):
        queryset = self.grades.filter(user=user)
        if queryset.exists():
            return queryset.first().grade.get_base_grade()
        return KnowledgeGradeScale.objects.first().get_base_grade()

    def get_common_grades(self, request):
        variant = request.GET.get('variant')
        if variant and variant.isdigit():
            variant = int(variant)
        else:
            variant = 2

        proof_base_value = self.get_proof_base_grade(request, variant)
        if not proof_base_value:
            proof_base_value = KnowledgeGradeScale.objects.all().first().get_base_grade()
        common_grade_value = (
            proof_base_value + self.get_users_grade(request.user)) / 2
        return common_grade_value, proof_base_value

    def get_proof_base_grade(self, request, variant=2, sum_list=None, base_flag=True):
        if sum_list is None:
            sum_list = []

        queryset = self.base.filter(
            tr__is_argument=True,
            rz__tz__can_be_rated=True,
        )
        summ = 0
        if queryset.exists():
            if variant == 1:
                sum_list.append(sum(map(lambda x: x.rz.get_users_grade(
                    request.user), queryset)) / len(queryset))
            else:
                sum_list.append(
                    sum(map(lambda x: x.get_proof_weight(request.user), queryset)) / len(queryset))

            for relation in queryset:
                child = relation.rz
                child_list = child.get_proof_base_grade(
                    request, sum_list=sum_list, base_flag=False)
                cl = list(filter(lambda x: x > 0, child_list))
                if cl:
                    summ += sum(cl) / len(cl)
            if summ:
                sum_list.append(summ)

        if base_flag:
            sum_list = list(filter(lambda x: x > 0, sum_list))
            if sum_list:
                return sum(sum_list) / len(sum_list)
            else:
                return 0
        return [summ]

    class Meta:
        verbose_name = 'Знание'
        verbose_name_plural = 'Знания'
        ordering = ('order',)
