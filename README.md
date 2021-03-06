# LiSCU Dataset
LiSCU is a dataset of literary pieces and their summaries paired with descriptions of characters that appear in them (presented by [_"Let Your Characters Tell Their Story": A Dataset for Character-Centric Narrative Understanding_](https://arxiv.org/abs/2109.05438)). It was created from various online study guides such as [shmoop](https://www.shmoop.com/study-guides/literature), [SparkNotes](https://www.sparknotes.com/lit/), [CliffsNotes](https://www.cliffsnotes.com/literature), and [LitCharts](https://www.litcharts.com). 

This repo provides a way to reproduce the dataset from [Wayback Machine](https://archive.org/web/), a time-stamped digital archive of the web.

## Requirements
- The reproducing process uses PostgreSQL as an interim data storage when crawling data from Wayback Machine. Please install it before starting the process. You can download it on its [official website](https://www.postgresql.org/download/).

- Connecting to the PostgreSQL database requires a database username and its password. Please prepare them before starting the process. It is highly recommended to create a dedicated database user for the process to avoid any unexpected modification on other databases you created previously.

- The process also uses some open-sourced python packages. You can download them by running the following command.
> $ pip install -r requirements.txt

- We encourage you to use virtual environments when recreating the dataset. The recommended Python version is 3.8.

## Generating the dataset
First, generate the running script by running the following command.
> python generate_run_script.py -o <output_dir> -i <database_name> --user <database_username> --password <database_user_password> \[--skip_scraping\]

**output_dir** is the path to the directory you want to export the dataset to. **database_name** is the database you want to create for storing the scraped data from Wayback Machine. **database_usename** and **database_user_password** are the username and password you prepared for this reproducing process.

```
Note: If "skip_scraping" is enabled, the generated script will only run processes after the data have been scraped. Only use this flag when you have already run the scraping process completely.
```

Then, run the generated script to start the reproducing process.
> ./run.sh


The process may take a few hours to be finished. After the process finishes, you can find all recreated datasets at the **output_dir**. To be more specific, there will be 4 jsonl files in the **output_dir**:

- liscu_all.jsonl
- liscu_train.jsonl
- liscu_test.jsonl
- liscu_val.jsonl
