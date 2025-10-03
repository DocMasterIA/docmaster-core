
# @admin.register(Snippet)
# class SnippetAdmin(admin.ModelAdmin):
#     list_display = ("name", "area", "short_content", "active", "order")
#     list_filter = ("area", "active")
#     search_fields = ("name", "content", "slug")
#     ordering = ("order", "name")
#     readonly_fields = ()
#     fieldsets = (
#         (None, {"fields": ("name", "slug", "area", "content")}),
#         ("Configurações", {"fields": ("tags", "active", "order")}),
#     )

#     def short_content(self, obj):
#         txt = (obj.content or "").strip()
#         return txt[:80] + ("..." if len(txt) > 80 else "")
#     short_content.short_description = "Conteúdo resumido"


# @admin.register(Rule)
# class RuleAdmin(admin.ModelAdmin):
#     list_display = ("field_name", "match_value", "snippets_list", "order")
#     list_filter = ("field_name", "match_value")
#     search_fields = ("field_name", "match_value")
#     ordering = ("order",)

#     filter_horizontal = ("snippets",)  # permite selecionar múltiplos snippets com interface melhor

#     def snippets_list(self, obj):
#         return ", ".join([s.name for s in obj.snippets.all()])
#     snippets_list.short_description = "Snippets"
