---
hide:
  - toc
---

A Parquet file is a special type of data file that's designed to store large amounts of information in a way that's really efficient and easy to work with. It's kind of like a digital filing cabinet for your data.

Parquet files are really handy for working with large, complex datasets. They're super efficient, fast, and flexible, which makes them a popular choice for a lot of big data and analytics applications.

Some of the key benefits of Parquet files include:

  - __Smaller file size__: The columnar storage and compression features make Parquet files much smaller than other data formats.
  - __Faster performance__: Data is organized making it really quick and easy to find and access the specific information you need.
  - __Cross-platform__: They can be used with all kinds of different tools and frameworks, so you can share your data anywhere.
  - __Metadata support__: They store information about the data structure and schema, which makes them really easy to work with.

!!! note "Parquet parameters"

    ### __Required__ parameters are in __red__{ .fc-red } and __Optional__ parameters are in __blue__{ .fc-blue }.
    
    ---

    - [x] __directory__{ .fc-red }, _the folder location to write JSON files to_

    ---

    - [ ] __compression__{ .fc-blue }, _the method used to compress data_
    <br />__default__{ .fc-gray }: `GZIP` ( __allowed__{ .fc-green }: `GZIP`, `SNAPPY` )


??? question "How do I use the Parquet syncer in commands?"

    `cs_tools tools searchable bi-server --syncer parquet://directory=.`

    __- or -__{ .fc-blue }

    `cs_tools tools searchable bi-server --syncer parquet://definition.toml`


## Definition TOML Example

`definition.toml`
```toml
[configuration]
directory = '...'
compression = 'SNAPPY'
```