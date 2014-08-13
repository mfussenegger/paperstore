
create table docs (
    id string primary key,
    content string index using fulltext with (analyzer = 'german'),
    tags array(string),
    preview_hash string,
    pdf_hash string,
    ts timestamp
) with (number_of_replicas = '0-2');


create blob table docs with (number_of_replicas = '0-2');
