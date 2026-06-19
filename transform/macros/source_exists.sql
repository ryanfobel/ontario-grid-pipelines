{# Returns true if a table exists in the given schema (defaults to 'raw'). #}
{% macro source_exists(table_name, schema='raw') %}
  {% set query %}
    select count(*) from information_schema.tables
    where table_schema = '{{ schema }}' and table_name = '{{ table_name }}'
  {% endset %}
  {% set result = run_query(query) %}
  {% if execute %}
    {{ return(result.columns[0].values()[0] > 0) }}
  {% else %}
    {{ return(true) }}
  {% endif %}
{% endmacro %}
