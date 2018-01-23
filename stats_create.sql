DROP TABLE IF EXISTS `stats`;
CREATE TABLE IF NOT EXISTS `stats` (
	`device_id` INT(4) UNSIGNED NOT NULL,
	`host` CHAR(16) NOT NULL,
	`mname` CHAR(16) NOT NULL,
	`set_timestamp` INT(4) UNSIGNED NOT NULL,
	`walk_timestamp` INT(4) UNSIGNED NOT NULL,
	`queries` INT(4) UNSIGNED NOT NULL,
	`avail` INT(4) UNSIGNED NOT NULL,
	`metrics` INT(4) UNSIGNED NOT NULL,
	`errors` INT(4) UNSIGNED NOT NULL,
	`time` INT(4) UNSIGNED NOT NULL,
	PRIMARY KEY (`device_id`),
	INDEX `host` (`host`)
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB;
