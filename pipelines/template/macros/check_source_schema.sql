{#
  Preflight: compare the REAL structure of each source table (information_schema) with the expected columns and types declared
  in models/sources.yml and FAIL EARLY with a clear message when they differ. Run: dbt run-operation check_source_schema
  (the Airflow DAG runs it before every transformation task). Only DECLARED columns are checked: a column added at the source
  does not break the pipeline. Safe widening (integer -> decimal -> float, date -> timestamp) is accepted; every other type
  change is an error. Keep this file ASCII: dbt reads it with the OS locale encoding.
#}

{% macro p113_type_family(data_type) %}
  {% set t = (data_type | string | lower).split('(')[0].split(' ')[0] %}
  {% if t in ['tinyint', 'smallint', 'integer', 'int', 'bigint', 'hugeint', 'ubigint', 'int2', 'int4', 'int8'] %}
    {{ return('integer') }}
  {% elif t in ['decimal', 'numeric'] %}
    {{ return('decimal') }}
  {% elif t in ['double', 'float', 'real', 'float4', 'float8'] %}
    {{ return('float') }}
  {% elif t in ['varchar', 'text', 'char', 'string', 'bpchar', 'character', 'uuid'] %}
    {{ return('string') }}
  {% elif t in ['boolean', 'bool'] %}
    {{ return('boolean') }}
  {% elif t == 'date' %}
    {{ return('date') }}
  {% elif t in ['timestamp', 'timestamptz', 'datetime'] %}
    {{ return('timestamp') }}
  {% elif t in ['json', 'jsonb', 'struct', 'map'] %}
    {{ return('json') }}
  {% endif %}
  {{ return('other') }}
{% endmacro %}

{% macro p113_type_ok(expected, actual) %}
  {% set safe = [['integer', 'decimal'], ['integer', 'float'], ['decimal', 'float'], ['date', 'timestamp']] %}
  {% set want = p113_type_family(expected) | trim %}
  {% set got = p113_type_family(actual) | trim %}
  {{ return(want == got or [want, got] in safe) }}
{% endmacro %}

{% macro check_source_schema() %}
  {% set problems = [] %}
  {% if execute %}
    {% for node in graph.sources.values() %}
      {% set expected = node.columns %}
      {% if expected | length > 0 %}
        {% set query %}
          select lower(column_name), lower(data_type)
          from information_schema.columns
          where table_schema = '{{ node.schema }}' and table_name = '{{ node.identifier }}'
        {% endset %}
        {% set found = {} %}
        {% for row in run_query(query).rows %}
          {% do found.update({row[0]: row[1]}) %}
        {% endfor %}
        {% if found | length == 0 %}
          {% do problems.append('Bang nguon ' ~ node.name ~ ' khong con o nguon (hoac khong doc duoc).') %}
        {% else %}
          {% for name, column in expected.items() %}
            {% if (name | lower) not in found %}
              {% do problems.append('Cot ' ~ node.name ~ '.' ~ name ~ ' khong con o nguon.') %}
            {% elif column.data_type and not p113_type_ok(column.data_type, found[name | lower]) %}
              {% do problems.append('Cot ' ~ node.name ~ '.' ~ name ~ ' doi kieu: ky vong ' ~ column.data_type ~ ', thuc te ' ~ found[name | lower] ~ '.') %}
            {% endif %}
          {% endfor %}
        {% endif %}
      {% endif %}
    {% endfor %}
  {% endif %}
  {% if problems | length > 0 %}
    {{ exceptions.raise_compiler_error('P113_SOURCE_SCHEMA_CHANGED: cau truc nguon da doi so voi luc sinh pipeline:' ~ '\n- ' ~ (problems | join('\n- '))) }}
  {% endif %}
  {{ log('check_source_schema: cau truc nguon khop voi khai bao.', info=True) }}
{% endmacro %}
