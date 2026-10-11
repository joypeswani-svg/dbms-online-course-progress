-- ============================================================================
-- Project 34: Online Course Learning Progress Management System
-- Database Schema (MySQL 8.0+)
-- Fully 3NF Normalized with Constraints, Triggers, and Indexes
-- ============================================================================

DROP DATABASE IF EXISTS `course_progress_db`;
CREATE DATABASE `course_progress_db` 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE `course_progress_db`;

-- Drop existing tables in reverse dependency order if recreating
SET FOREIGN_KEY_CHECKS = 0;
DROP TRIGGER IF EXISTS `trg_check_quiz_attempt_limit`;
DROP TRIGGER IF EXISTS `trg_check_certificate_eligibility`;
DROP TABLE IF EXISTS `feedback`;
DROP TABLE IF EXISTS `certificates`;
DROP TABLE IF EXISTS `responses`;
DROP TABLE IF EXISTS `attempts`;
DROP TABLE IF EXISTS `questions`;
DROP TABLE IF EXISTS `quizzes`;
DROP TABLE IF EXISTS `lesson_progress`;
DROP TABLE IF EXISTS `enrolments`;
DROP TABLE IF EXISTS `lessons`;
DROP TABLE IF EXISTS `modules`;
DROP TABLE IF EXISTS `courses`;
DROP TABLE IF EXISTS `learners`;
DROP TABLE IF EXISTS `instructors`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 1. USERS TABLE
-- Authentication & Core Profile (Role-Prefixed ID: A01, I01-I05, L01-L20)
-- ----------------------------------------------------------------------------
CREATE TABLE `users` (
  `id` VARCHAR(20) PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'instructor', 'learner') NOT NULL DEFAULT 'learner',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_users_email` UNIQUE (`email`),
  CONSTRAINT `chk_users_email_format` CHECK (
    `email` REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'
  )
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. INSTRUCTORS TABLE
-- Instructor Profiles (1:1 with users having role = 'instructor', e.g. I01-I05)
-- ----------------------------------------------------------------------------
CREATE TABLE `instructors` (
  `id` VARCHAR(20) PRIMARY KEY,
  `user_id` VARCHAR(20) NOT NULL,
  `title` VARCHAR(120) NOT NULL DEFAULT 'Course Instructor',
  `expertise` VARCHAR(255) NOT NULL,
  `bio` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_instructors_user_id` UNIQUE (`user_id`),
  CONSTRAINT `fk_instructors_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. LEARNERS TABLE
-- Learner Profiles (1:1 with users having role = 'learner', e.g. L01-L20)
-- ----------------------------------------------------------------------------
CREATE TABLE `learners` (
  `id` VARCHAR(20) PRIMARY KEY,
  `user_id` VARCHAR(20) NOT NULL,
  `headline` VARCHAR(200) NULL DEFAULT 'Lifelong Learner',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_learners_user_id` UNIQUE (`user_id`),
  CONSTRAINT `fk_learners_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. COURSES TABLE
-- Courses authored by instructors
-- ----------------------------------------------------------------------------
CREATE TABLE `courses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `instructor_id` VARCHAR(20) NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `slug` VARCHAR(220) NOT NULL,
  `category` VARCHAR(100) NOT NULL,
  `difficulty` ENUM('beginner', 'intermediate', 'advanced') NOT NULL DEFAULT 'beginner',
  `description` TEXT NOT NULL,
  `price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
  `passing_score` INT NOT NULL DEFAULT 70,
  `thumbnail_url` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_courses_slug` UNIQUE (`slug`),
  CONSTRAINT `chk_courses_price` CHECK (`price` >= 0.00),
  CONSTRAINT `chk_courses_passing_score` CHECK (`passing_score` >= 0 AND `passing_score` <= 100),
  CONSTRAINT `fk_courses_instructor` FOREIGN KEY (`instructor_id`)
    REFERENCES `instructors` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 5. MODULES TABLE
-- Course sections/modules
-- ----------------------------------------------------------------------------
CREATE TABLE `modules` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `course_id` INT NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `order_num` INT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_modules_course_order` UNIQUE (`course_id`, `order_num`),
  CONSTRAINT `chk_modules_order_num` CHECK (`order_num` >= 1),
  CONSTRAINT `fk_modules_course` FOREIGN KEY (`course_id`)
    REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 6. LESSONS TABLE
-- Educational units within modules
-- ----------------------------------------------------------------------------
CREATE TABLE `lessons` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `module_id` INT NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `content_type` ENUM('video', 'reading', 'interactive') NOT NULL DEFAULT 'reading',
  `content` TEXT NULL,
  `duration_minutes` INT NOT NULL DEFAULT 15,
  `order_num` INT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_lessons_module_order` UNIQUE (`module_id`, `order_num`),
  CONSTRAINT `chk_lessons_order_num` CHECK (`order_num` >= 1),
  CONSTRAINT `chk_lessons_duration` CHECK (`duration_minutes` >= 0),
  CONSTRAINT `fk_lessons_module` FOREIGN KEY (`module_id`)
    REFERENCES `modules` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 7. ENROLMENTS TABLE
-- Enrollment tracking per learner per course
-- ----------------------------------------------------------------------------
CREATE TABLE `enrolments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `learner_id` VARCHAR(20) NOT NULL,
  `course_id` INT NOT NULL,
  `status` ENUM('active', 'completed', 'dropped') NOT NULL DEFAULT 'active',
  `progress` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `enrolled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  `dropped_at` DATETIME NULL,
  CONSTRAINT `uq_enrolments_learner_course` UNIQUE (`learner_id`, `course_id`),
  CONSTRAINT `chk_enrolments_progress_range` CHECK (`progress` >= 0.00 AND `progress` <= 100.00),
  CONSTRAINT `fk_enrolments_learner` FOREIGN KEY (`learner_id`)
    REFERENCES `learners` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_enrolments_course` FOREIGN KEY (`course_id`)
    REFERENCES `courses` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 8. LESSON_PROGRESS TABLE
-- Completion state per lesson per enrolment
-- ----------------------------------------------------------------------------
CREATE TABLE `lesson_progress` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `enrolment_id` INT NOT NULL,
  `lesson_id` INT NOT NULL,
  `is_completed` BOOLEAN NOT NULL DEFAULT FALSE,
  `completed_at` DATETIME NULL,
  `last_accessed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `uq_lesson_progress_enrolment_lesson` UNIQUE (`enrolment_id`, `lesson_id`),
  CONSTRAINT `fk_lesson_progress_enrolment` FOREIGN KEY (`enrolment_id`)
    REFERENCES `enrolments` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_lesson_progress_lesson` FOREIGN KEY (`lesson_id`)
    REFERENCES `lessons` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 9. QUIZZES TABLE
-- Assessments attached to modules
-- ----------------------------------------------------------------------------
CREATE TABLE `quizzes` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `module_id` INT NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `total_marks` INT NOT NULL DEFAULT 100,
  `passing_marks` INT NOT NULL DEFAULT 70,
  `max_attempts` INT NOT NULL DEFAULT 3,
  `time_limit_mins` INT NOT NULL DEFAULT 20,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `chk_quizzes_total_marks` CHECK (`total_marks` > 0),
  CONSTRAINT `chk_quizzes_passing_marks` CHECK (`passing_marks` >= 0 AND `passing_marks` <= `total_marks`),
  CONSTRAINT `chk_quizzes_max_attempts` CHECK (`max_attempts` >= 1),
  CONSTRAINT `chk_quizzes_time_limit` CHECK (`time_limit_mins` >= 0),
  CONSTRAINT `fk_quizzes_module` FOREIGN KEY (`module_id`)
    REFERENCES `modules` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 10. QUESTIONS TABLE
-- Multiple choice questions with Options A-D and Correct Option
-- ----------------------------------------------------------------------------
CREATE TABLE `questions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `quiz_id` INT NOT NULL,
  `question_text` TEXT NOT NULL,
  `option_a` VARCHAR(255) NOT NULL,
  `option_b` VARCHAR(255) NOT NULL,
  `option_c` VARCHAR(255) NOT NULL,
  `option_d` VARCHAR(255) NOT NULL,
  `correct_option` ENUM('A', 'B', 'C', 'D') NOT NULL,
  `marks` INT NOT NULL DEFAULT 20,
  `order_num` INT NOT NULL DEFAULT 1,
  CONSTRAINT `uq_questions_quiz_order` UNIQUE (`quiz_id`, `order_num`),
  CONSTRAINT `chk_questions_order_num` CHECK (`order_num` >= 1),
  CONSTRAINT `chk_questions_marks` CHECK (`marks` > 0),
  CONSTRAINT `fk_questions_quiz` FOREIGN KEY (`quiz_id`)
    REFERENCES `quizzes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 11. ATTEMPTS TABLE
-- Learner quiz attempts with scores and pass/fail state
-- ----------------------------------------------------------------------------
CREATE TABLE `attempts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `quiz_id` INT NOT NULL,
  `learner_id` VARCHAR(20) NOT NULL,
  `attempt_number` INT NOT NULL DEFAULT 1,
  `score` DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  `total_marks` DECIMAL(6,2) NOT NULL DEFAULT 100.00,
  `is_passed` BOOLEAN NOT NULL DEFAULT FALSE,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `submitted_at` DATETIME NULL,
  CONSTRAINT `uq_attempts_quiz_learner_num` UNIQUE (`quiz_id`, `learner_id`, `attempt_number`),
  CONSTRAINT `chk_attempts_number` CHECK (`attempt_number` >= 1),
  CONSTRAINT `chk_attempts_total_marks` CHECK (`total_marks` > 0),
  CONSTRAINT `chk_attempts_score_range` CHECK (`score` >= 0.00 AND `score` <= `total_marks`),
  CONSTRAINT `fk_attempts_quiz` FOREIGN KEY (`quiz_id`)
    REFERENCES `quizzes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_attempts_learner` FOREIGN KEY (`learner_id`)
    REFERENCES `learners` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 12. RESPONSES TABLE
-- Individual question responses for each attempt
-- ----------------------------------------------------------------------------
CREATE TABLE `responses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `attempt_id` INT NOT NULL,
  `question_id` INT NOT NULL,
  `chosen_option` ENUM('A', 'B', 'C', 'D') NULL,
  `is_correct` BOOLEAN NOT NULL DEFAULT FALSE,
  `marks_obtained` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT `uq_responses_attempt_question` UNIQUE (`attempt_id`, `question_id`),
  CONSTRAINT `chk_responses_marks` CHECK (`marks_obtained` >= 0.00),
  CONSTRAINT `fk_responses_attempt` FOREIGN KEY (`attempt_id`)
    REFERENCES `attempts` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_responses_question` FOREIGN KEY (`question_id`)
    REFERENCES `questions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 13. CERTIFICATES TABLE
-- Issued upon successful 100% completion & all quizzes passed
-- ----------------------------------------------------------------------------
CREATE TABLE `certificates` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `enrolment_id` INT NOT NULL,
  `certificate_code` VARCHAR(64) NOT NULL,
  `issued_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `certificate_url` VARCHAR(255) NULL,
  CONSTRAINT `uq_certificates_enrolment` UNIQUE (`enrolment_id`),
  CONSTRAINT `uq_certificates_code` UNIQUE (`certificate_code`),
  CONSTRAINT `fk_certificates_enrolment` FOREIGN KEY (`enrolment_id`)
    REFERENCES `enrolments` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 14. FEEDBACK TABLE
-- Course feedback and rating by enrolled learners
-- ----------------------------------------------------------------------------
CREATE TABLE `feedback` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `enrolment_id` INT NOT NULL,
  `rating` INT NOT NULL,
  `review_title` VARCHAR(150) NULL,
  `comments` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `uq_feedback_enrolment` UNIQUE (`enrolment_id`),
  CONSTRAINT `chk_feedback_rating_range` CHECK (`rating` >= 1 AND `rating` <= 5),
  CONSTRAINT `fk_feedback_enrolment` FOREIGN KEY (`enrolment_id`)
    REFERENCES `enrolments` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- INDEXES
-- Optimized for search, filtering, and foreign key traversals
-- ============================================================================
CREATE INDEX `idx_users_role` ON `users` (`role`);
CREATE INDEX `idx_courses_title` ON `courses` (`title`);
CREATE INDEX `idx_courses_status` ON `courses` (`status`);
CREATE INDEX `idx_courses_category_status` ON `courses` (`category`, `status`);
CREATE INDEX `idx_enrolments_learner` ON `enrolments` (`learner_id`);
CREATE INDEX `idx_enrolments_course` ON `enrolments` (`course_id`);
CREATE INDEX `idx_enrolments_status` ON `enrolments` (`status`);
CREATE INDEX `idx_attempts_learner_quiz` ON `attempts` (`learner_id`, `quiz_id`);
CREATE INDEX `idx_attempts_quiz_learner` ON `attempts` (`quiz_id`, `learner_id`);
CREATE INDEX `idx_lesson_progress_enrolment` ON `lesson_progress` (`enrolment_id`);
CREATE INDEX `idx_certificates_code` ON `certificates` (`certificate_code`);

-- ============================================================================
-- TRIGGERS
-- Database-level business rules enforcement
-- ============================================================================

DELIMITER $$

-- ----------------------------------------------------------------------------
-- Trigger 1: Block Quiz Attempts Exceeding max_attempts
-- ----------------------------------------------------------------------------
CREATE TRIGGER `trg_check_quiz_attempt_limit`
BEFORE INSERT ON `attempts`
FOR EACH ROW
BEGIN
  DECLARE v_max_attempts INT DEFAULT 3;
  DECLARE v_current_attempts INT DEFAULT 0;

  -- Get max_attempts allowed for this quiz
  SELECT `max_attempts` INTO v_max_attempts
  FROM `quizzes`
  WHERE `id` = NEW.quiz_id;

  -- Count existing attempts by this learner for this quiz
  SELECT COUNT(*) INTO v_current_attempts
  FROM `attempts`
  WHERE `quiz_id` = NEW.quiz_id
    AND `learner_id` = NEW.learner_id;

  IF v_current_attempts >= v_max_attempts THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Maximum quiz attempt limit reached for this quiz';
  END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 2: Enforce Certificate Issuance Eligibility
-- (Enrolment completed, 100% progress, all lessons complete, all quizzes passed)
-- ----------------------------------------------------------------------------
CREATE TRIGGER `trg_check_certificate_eligibility`
BEFORE INSERT ON `certificates`
FOR EACH ROW
BEGIN
  DECLARE v_status ENUM('active', 'completed', 'dropped');
  DECLARE v_progress DECIMAL(5,2);
  DECLARE v_course_id INT;
  DECLARE v_learner_id VARCHAR(20);
  DECLARE v_total_lessons INT DEFAULT 0;
  DECLARE v_completed_lessons INT DEFAULT 0;
  DECLARE v_total_quizzes INT DEFAULT 0;
  DECLARE v_passed_quizzes INT DEFAULT 0;

  -- Retrieve enrolment details
  SELECT `status`, `progress`, `course_id`, `learner_id`
  INTO v_status, v_progress, v_course_id, v_learner_id
  FROM `enrolments`
  WHERE `id` = NEW.enrolment_id;

  IF v_course_id IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Certificate error: Enrolment not found';
  END IF;

  -- Rule 1: Enrolment must be marked completed and have progress = 100.00%
  IF v_status != 'completed' OR v_progress < 100.00 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Certificate rejected: Enrolment is not completed (100% progress required)';
  END IF;

  -- Rule 2: All lessons in the course must be marked completed
  SELECT COUNT(l.id) INTO v_total_lessons
  FROM `lessons` l
  JOIN `modules` m ON l.module_id = m.id
  WHERE m.course_id = v_course_id;

  SELECT COUNT(lp.id) INTO v_completed_lessons
  FROM `lesson_progress` lp
  JOIN `lessons` l ON lp.lesson_id = l.id
  JOIN `modules` m ON l.module_id = m.id
  WHERE lp.enrolment_id = NEW.enrolment_id
    AND m.course_id = v_course_id
    AND lp.is_completed = TRUE;

  IF v_total_lessons > 0 AND v_completed_lessons < v_total_lessons THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Certificate rejected: Not all course lessons have been completed';
  END IF;

  -- Rule 3: All quizzes in the course must have at least one passed attempt by the learner
  SELECT COUNT(q.id) INTO v_total_quizzes
  FROM `quizzes` q
  JOIN `modules` m ON q.module_id = m.id
  WHERE m.course_id = v_course_id;

  IF v_total_quizzes > 0 THEN
    SELECT COUNT(DISTINCT q.id) INTO v_passed_quizzes
    FROM `quizzes` q
    JOIN `modules` m ON q.module_id = m.id
    JOIN `attempts` a ON a.quiz_id = q.id
    WHERE m.course_id = v_course_id
      AND a.learner_id = v_learner_id
      AND a.is_passed = TRUE;

    IF v_passed_quizzes < v_total_quizzes THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Certificate rejected: All course quizzes must be passed prior to certification';
    END IF;
  END IF;

END$$

DELIMITER ;
