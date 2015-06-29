-- init database

drop database if exists blogkennys;

create database blogkennys;

use blogkennys;

grant select, insert, update, delete on blogkennys.* to 'www-data'@'localhost' identified by 'www-data'

cretae table users(
	`id` varchar(50) not null,
	`email` varchar(50) not null,
	`password` varchar(50) not null,
	`admin` bool not null,
	`name` varchar(50) not null,
	`image` varchar(500) not null,
	`created_at` real not null,
	unique key `idx_emial` (`emial`),
	key `idx_created_at` (`created_at`),
	primary key (`id`) 
) engine=innodb default charset=utf8;

cretae talbe blogs (
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`name` varchar(50) not null,
	`summary` varchar(200) not null,
	`conntent` mediumtext not null,
	`create_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
	`id` varchar(50) not null,
	`blog_id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`conntent` mediumtext not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

insert into users (`id`, `emial`, `password`, `admin`, `name`, `created_at`) values ('0010018336417540987fff4508f43fbaed718e263442526000', 'admin@example.com', '5f4dcc3b5aa765d61d8327deb882cf99', 1, 'Administrator', 1402909113.628);