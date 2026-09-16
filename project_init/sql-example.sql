-- 1. 创建远程用户并授权（在 mysql 系统库执行，不需要 USE）
CREATE USER IF NOT EXISTS 'dochelper'@'%' IDENTIFIED WITH mysql_native_password BY 'CHANGE_YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON dochelper.* TO 'dochelper'@'%';
FLUSH PRIVILEGES;

-- 2. 创建业务数据库
CREATE DATABASE IF NOT EXISTS `dochelper`
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 3. 【关键】切换到这个数据库，下面的表都会建在这里
USE `dochelper`;

-- 4. 建表
CREATE TABLE `chunk` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `file_id` INT NOT NULL COMMENT 'chunk所在file的id',
    `title` VARCHAR(500) NOT NULL COMMENT 'chunk所在标题的标题名',
    `content` TEXT NOT NULL COMMENT '内容',
    `title_breadcrumb_path` VARCHAR(1000) NOT NULL COMMENT '标题结构，生成向量需要',
    `part` INT NOT NULL COMMENT 'chunk所在标题下第几个chunk',
    PRIMARY KEY (`id`)
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档内容分块表';

CREATE TABLE `main_body` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `file_id` INT NOT NULL COMMENT 'main_body所在file的id',
    `body_name` VARCHAR(500) NOT NULL COMMENT 'main_body名',
    PRIMARY KEY (`id`)
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档主体信息表';

CREATE TABLE `file` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
    `unique_name` VARCHAR(500) NOT NULL COMMENT 'uuid4编码的文件名',
    `origin_name` VARCHAR(500) NOT NULL COMMENT '用户上传的文件名',
    PRIMARY KEY (`id`)
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件信息表';