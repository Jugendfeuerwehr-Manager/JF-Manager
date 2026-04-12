from .models import Category, Item


def get_item_list():
    item_view_list = Item.objects.all()
    return item_view_list


def get_category_list():
    category_view_list = Category.objects.all()
    return category_view_list
