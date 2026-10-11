-- ============================================================================
-- Project 34: Online Course Learning Progress Management System
-- Stored Procedures with Transactions & Robust Error Handling
-- ============================================================================

USE `course_progress_db`;

DROP PROCEDURE IF EXISTS `enroll_learner`;
DROP PROCEDURE IF EXISTS `complete_lesson`;
DROP PROCEDURE IF EXISTS `submit_quiz_attempt`;
DROP PROCEDURE IF EXISTS `issue_certificate`;

DELIMITER $$

-- ----------------------------------------------------------------------------
-- 1. enroll_learner
-- Transactional enrollment with validation and initial lesson progress seeding
-- ----------------------------------------------------------------------------
CREATE PROCEDURE `enroll_learner`(
  IN p_learner_id VARCHAR(20),
  IN p_course_id INT,
  OUT p_enrolment_id INT,
  OUT p_status_code VARCHAR(50),
  OUT p_message VARCHAR(255)
)
proc_body: BEGIN
  DECLARE v_learner_exists INT DEFAULT 0;
  DECLARE v_course_exists INT DEFAULT 0;
  DECLARE v_course_status VARCHAR(20);
  DECLARE v_already_enrolled INT DEFAULT 0;

  -- Error handler
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    SET p_enrolment_id = NULL;
    SET p_status_code = 'ERROR';
    SET p_message = 'Failed to enroll learner due to database exception.';
  END;

  SET p_enrolment_id = NULL;

  -- Validate learner
  SELECT COUNT(*) INTO v_learner_exists FROM `learners` WHERE `id` = p_learner_id;
  IF v_learner_exists = 0 THEN
    SET p_status_code = 'LEARNER_NOT_FOUND';
    SET p_message = 'Learner ID does not exist.';
    LEAVE proc_body;
  END IF;

  -- Validate course
  SELECT COUNT(*), MAX(`status`) INTO v_course_exists, v_course_status 
  FROM `courses` WHERE `id` = p_course_id;
  IF v_course_exists = 0 THEN
    SET p_status_code = 'COURSE_NOT_FOUND';
    SET p_message = 'Course ID does not exist.';
    LEAVE proc_body;
  END IF;

  -- Check existing enrollment
  SELECT COUNT(*) INTO v_already_enrolled 
  FROM `enrolments` 
  WHERE `learner_id` = p_learner_id AND `course_id` = p_course_id;

  IF v_already_enrolled > 0 THEN
    SET p_status_code = 'ALREADY_ENROLLED';
    SET p_message = 'Learner is already enrolled in this course.';
    LEAVE proc_body;
  END IF;

  START TRANSACTION;

  -- Insert enrollment record
  INSERT INTO `enrolments` (`learner_id`, `course_id`, `status`, `progress`, `enrolled_at`)
  VALUES (p_learner_id, p_course_id, 'active', 0.00, NOW());

  SET p_enrolment_id = LAST_INSERT_ID();

  -- Initialize lesson_progress for all lessons in the course
  INSERT INTO `lesson_progress` (`enrolment_id`, `lesson_id`, `is_completed`, `last_accessed_at`)
  SELECT p_enrolment_id, l.`id`, FALSE, NOW()
  FROM `lessons` l
  JOIN `modules` m ON l.`module_id` = m.`id`
  WHERE m.`course_id` = p_course_id
  ORDER BY m.`order_num`, l.`order_num`;

  COMMIT;

  SET p_status_code = 'SUCCESS';
  SET p_message = 'Learner enrolled successfully.';
END$$

-- ----------------------------------------------------------------------------
-- 2. complete_lesson
-- Marks lesson completed and dynamically recalculates overall course progress
-- ----------------------------------------------------------------------------
CREATE PROCEDURE `complete_lesson`(
  IN p_enrolment_id INT,
  IN p_lesson_id INT,
  OUT p_new_progress DECIMAL(5,2),
  OUT p_course_completed BOOLEAN,
  OUT p_message VARCHAR(255)
)
proc_body: BEGIN
  DECLARE v_course_id INT;
  DECLARE v_learner_id VARCHAR(20);
  DECLARE v_enrolment_status ENUM('active', 'completed', 'dropped');
  DECLARE v_total_lessons INT DEFAULT 0;
  DECLARE v_completed_lessons INT DEFAULT 0;
  DECLARE v_total_quizzes INT DEFAULT 0;
  DECLARE v_passed_quizzes INT DEFAULT 0;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    SET p_new_progress = 0.00;
    SET p_course_completed = FALSE;
    SET p_message = 'Database error while completing lesson.';
  END;

  -- Check enrollment
  SELECT `course_id`, `learner_id`, `status`
  INTO v_course_id, v_learner_id, v_enrolment_status
  FROM `enrolments`
  WHERE `id` = p_enrolment_id;

  IF v_course_id IS NULL THEN
    SET p_new_progress = 0.00;
    SET p_course_completed = FALSE;
    SET p_message = 'Enrolment ID not found.';
    LEAVE proc_body;
  END IF;

  START TRANSACTION;

  -- Upsert lesson progress
  INSERT INTO `lesson_progress` (`enrolment_id`, `lesson_id`, `is_completed`, `completed_at`, `last_accessed_at`)
  VALUES (p_enrolment_id, p_lesson_id, TRUE, NOW(), NOW())
  ON DUPLICATE KEY UPDATE 
    `is_completed` = TRUE,
    `completed_at` = COALESCE(`completed_at`, NOW()),
    `last_accessed_at` = NOW();

  -- Recalculate lessons in course
  SELECT COUNT(l.`id`) INTO v_total_lessons
  FROM `lessons` l
  JOIN `modules` m ON l.`module_id` = m.`id`
  WHERE m.`course_id` = v_course_id;

  SELECT COUNT(lp.`id`) INTO v_completed_lessons
  FROM `lesson_progress` lp
  JOIN `lessons` l ON lp.`lesson_id` = l.`id`
  JOIN `modules` m ON l.`module_id` = m.`id`
  WHERE lp.`enrolment_id` = p_enrolment_id
    AND m.`course_id` = v_course_id
    AND lp.`is_completed` = TRUE;

  IF v_total_lessons > 0 THEN
    SET p_new_progress = ROUND((v_completed_lessons / v_total_lessons) * 100.00, 2);
  ELSE
    SET p_new_progress = 100.00;
  END IF;

  -- Ensure progress stays within 0 and 100
  IF p_new_progress > 100.00 THEN
    SET p_new_progress = 100.00;
  END IF;

  -- Check quiz completion requirements
  SELECT COUNT(q.`id`) INTO v_total_quizzes
  FROM `quizzes` q
  JOIN `modules` m ON q.`module_id` = m.`id`
  WHERE m.`course_id` = v_course_id;

  IF v_total_quizzes > 0 THEN
    SELECT COUNT(DISTINCT q.`id`) INTO v_passed_quizzes
    FROM `quizzes` q
    JOIN `modules` m ON q.`module_id` = m.`id`
    JOIN `attempts` a ON a.`quiz_id` = q.`id`
    WHERE m.`course_id` = v_course_id
      AND a.`learner_id` = v_learner_id
      AND a.`is_passed` = TRUE;
  ELSE
    SET v_passed_quizzes = 0;
  END IF;

  -- Determine if course is fully completed
  IF p_new_progress >= 100.00 AND (v_total_quizzes = 0 OR v_passed_quizzes = v_total_quizzes) THEN
    SET p_course_completed = TRUE;
    UPDATE `enrolments`
    SET `progress` = 100.00,
        `status` = 'completed',
        `completed_at` = COALESCE(`completed_at`, NOW())
    WHERE `id` = p_enrolment_id;
  ELSE
    SET p_course_completed = FALSE;
    UPDATE `enrolments`
    SET `progress` = p_new_progress,
        `status` = IF(`status` = 'dropped', 'dropped', 'active')
    WHERE `id` = p_enrolment_id;
  END IF;

  COMMIT;

  SET p_message = 'Lesson marked complete and progress updated.';
END$$

-- ----------------------------------------------------------------------------
-- 3. submit_quiz_attempt
-- Atomic submission and auto-scoring of quiz attempt
-- Accepts JSON array of answers: [{"question_id": 1, "chosen_option": "A"}, ...]
-- ----------------------------------------------------------------------------
CREATE PROCEDURE `submit_quiz_attempt`(
  IN p_quiz_id INT,
  IN p_learner_id VARCHAR(20),
  IN p_answers_json JSON,
  OUT p_attempt_id INT,
  OUT p_score DECIMAL(6,2),
  OUT p_total_marks DECIMAL(6,2),
  OUT p_is_passed BOOLEAN,
  OUT p_message VARCHAR(255)
)
proc_body: BEGIN
  DECLARE v_max_attempts INT;
  DECLARE v_passing_marks INT;
  DECLARE v_existing_attempts INT DEFAULT 0;
  DECLARE v_next_attempt_num INT;
  DECLARE v_course_id INT;
  DECLARE v_enrolment_id INT;
  DECLARE v_all_lessons_done INT DEFAULT 0;
  DECLARE v_total_course_quizzes INT DEFAULT 0;
  DECLARE v_passed_course_quizzes INT DEFAULT 0;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    SET p_attempt_id = NULL;
    SET p_score = 0.00;
    SET p_total_marks = 0.00;
    SET p_is_passed = FALSE;
    SET p_message = 'Error processing quiz submission.';
  END;

  -- Verify quiz exists
  SELECT `max_attempts`, `passing_marks`, `total_marks`
  INTO v_max_attempts, v_passing_marks, p_total_marks
  FROM `quizzes`
  WHERE `id` = p_quiz_id;

  IF p_total_marks IS NULL THEN
    SET p_attempt_id = NULL;
    SET p_score = 0.00;
    SET p_is_passed = FALSE;
    SET p_message = 'Quiz not found.';
    LEAVE proc_body;
  END IF;

  -- Check attempt count
  SELECT COUNT(*) INTO v_existing_attempts
  FROM `attempts`
  WHERE `quiz_id` = p_quiz_id AND `learner_id` = p_learner_id;

  IF v_existing_attempts >= v_max_attempts THEN
    SET p_attempt_id = NULL;
    SET p_score = 0.00;
    SET p_is_passed = FALSE;
    SET p_message = 'Maximum quiz attempts exceeded.';
    LEAVE proc_body;
  END IF;

  SET v_next_attempt_num = v_existing_attempts + 1;

  START TRANSACTION;

  -- Insert initial attempt
  INSERT INTO `attempts` (`quiz_id`, `learner_id`, `attempt_number`, `score`, `total_marks`, `is_passed`, `started_at`, `submitted_at`)
  VALUES (p_quiz_id, p_learner_id, v_next_attempt_num, 0.00, p_total_marks, FALSE, NOW(), NOW());

  SET p_attempt_id = LAST_INSERT_ID();

  -- Record responses and calculate marks using JSON_TABLE
  INSERT INTO `responses` (`attempt_id`, `question_id`, `chosen_option`, `is_correct`, `marks_obtained`)
  SELECT 
    p_attempt_id,
    q.`id` AS question_id,
    ans.`chosen_opt` AS chosen_option,
    COALESCE(ans.`chosen_opt` COLLATE utf8mb4_unicode_ci = q.`correct_option`, FALSE) AS is_correct,
    IF(ans.`chosen_opt` IS NOT NULL AND ans.`chosen_opt` COLLATE utf8mb4_unicode_ci = q.`correct_option`, q.`marks`, 0.00) AS marks_obtained
  FROM `questions` q
  LEFT JOIN JSON_TABLE(
    p_answers_json,
    '$[*]' COLUMNS (
      q_id INT PATH '$.question_id',
      chosen_opt VARCHAR(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PATH '$.chosen_option'
    )
  ) ans ON q.`id` = ans.q_id
  WHERE q.`quiz_id` = p_quiz_id;

  -- Calculate total score obtained
  SELECT COALESCE(SUM(`marks_obtained`), 0.00)
  INTO p_score
  FROM `responses`
  WHERE `attempt_id` = p_attempt_id;

  SET p_is_passed = (p_score >= v_passing_marks);

  -- Update attempt with final score
  UPDATE `attempts`
  SET `score` = p_score,
      `is_passed` = p_is_passed
  WHERE `id` = p_attempt_id;

  -- Check if this now completes the course enrolment if progress was 100%
  SELECT m.`course_id` INTO v_course_id
  FROM `quizzes` q
  JOIN `modules` m ON q.`module_id` = m.`id`
  WHERE q.`id` = p_quiz_id;

  SELECT `id` INTO v_enrolment_id
  FROM `enrolments`
  WHERE `learner_id` = p_learner_id AND `course_id` = v_course_id;

  IF v_enrolment_id IS NOT NULL AND p_is_passed = TRUE THEN
    -- Check if all course lessons are completed
    SELECT (COUNT(l.`id`) = COUNT(lp.`id`)) INTO v_all_lessons_done
    FROM `lessons` l
    JOIN `modules` m ON l.`module_id` = m.`id`
    LEFT JOIN `lesson_progress` lp ON lp.`lesson_id` = l.`id` 
      AND lp.`enrolment_id` = v_enrolment_id AND lp.`is_completed` = TRUE
    WHERE m.`course_id` = v_course_id;

    -- Check if all course quizzes are passed
    SELECT COUNT(q.`id`) INTO v_total_course_quizzes
    FROM `quizzes` q
    JOIN `modules` m ON q.`module_id` = m.`id`
    WHERE m.`course_id` = v_course_id;

    SELECT COUNT(DISTINCT q.`id`) INTO v_passed_course_quizzes
    FROM `quizzes` q
    JOIN `modules` m ON q.`module_id` = m.`id`
    JOIN `attempts` a ON a.`quiz_id` = q.`id`
    WHERE m.`course_id` = v_course_id
      AND a.`learner_id` = p_learner_id
      AND a.`is_passed` = TRUE;

    IF v_all_lessons_done = 1 AND v_passed_course_quizzes >= v_total_course_quizzes THEN
      UPDATE `enrolments`
      SET `status` = 'completed',
          `progress` = 100.00,
          `completed_at` = COALESCE(`completed_at`, NOW())
      WHERE `id` = v_enrolment_id;
    END IF;
  END IF;

  COMMIT;

  SET p_message = IF(p_is_passed, 'Quiz passed successfully!', 'Quiz completed. Passing score not reached.');
END$$

-- ----------------------------------------------------------------------------
-- 4. issue_certificate
-- Verifies 100% lesson progress & quiz passing, generating unique certificate
-- ----------------------------------------------------------------------------
CREATE PROCEDURE `issue_certificate`(
  IN p_enrolment_id INT,
  OUT p_cert_code VARCHAR(64),
  OUT p_status_code VARCHAR(50),
  OUT p_message VARCHAR(255)
)
proc_body: BEGIN
  DECLARE v_status ENUM('active', 'completed', 'dropped');
  DECLARE v_progress DECIMAL(5,2);
  DECLARE v_course_id INT;
  DECLARE v_learner_id VARCHAR(20);
  DECLARE v_existing_code VARCHAR(64);
  DECLARE v_total_lessons INT DEFAULT 0;
  DECLARE v_completed_lessons INT DEFAULT 0;
  DECLARE v_total_quizzes INT DEFAULT 0;
  DECLARE v_passed_quizzes INT DEFAULT 0;
  DECLARE v_new_code VARCHAR(64);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    SET p_cert_code = NULL;
    SET p_status_code = 'ERROR';
    SET p_message = 'Failed to issue certificate due to database exception.';
  END;

  -- Check if already issued
  SELECT `certificate_code` INTO v_existing_code
  FROM `certificates`
  WHERE `enrolment_id` = p_enrolment_id;

  IF v_existing_code IS NOT NULL THEN
    SET p_cert_code = v_existing_code;
    SET p_status_code = 'ALREADY_ISSUED';
    SET p_message = 'Certificate has already been issued for this enrollment.';
    LEAVE proc_body;
  END IF;

  -- Verify enrollment exists
  SELECT `status`, `progress`, `course_id`, `learner_id`
  INTO v_status, v_progress, v_course_id, v_learner_id
  FROM `enrolments`
  WHERE `id` = p_enrolment_id;

  IF v_course_id IS NULL THEN
    SET p_cert_code = NULL;
    SET p_status_code = 'NOT_FOUND';
    SET p_message = 'Enrolment ID does not exist.';
    LEAVE proc_body;
  END IF;

  -- Eligibility Check 1: Progress must be 100% and status completed
  IF v_status != 'completed' OR v_progress < 100.00 THEN
    SET p_cert_code = NULL;
    SET p_status_code = 'NOT_ELIGIBLE';
    SET p_message = 'Ineligible: Enrolment progress must be 100% completed.';
    LEAVE proc_body;
  END IF;

  -- Eligibility Check 2: All lessons completed
  SELECT COUNT(l.`id`) INTO v_total_lessons
  FROM `lessons` l
  JOIN `modules` m ON l.`module_id` = m.`id`
  WHERE m.`course_id` = v_course_id;

  SELECT COUNT(lp.`id`) INTO v_completed_lessons
  FROM `lesson_progress` lp
  JOIN `lessons` l ON lp.`lesson_id` = l.`id`
  JOIN `modules` m ON l.`module_id` = m.`id`
  WHERE lp.`enrolment_id` = p_enrolment_id
    AND m.`course_id` = v_course_id
    AND lp.`is_completed` = TRUE;

  IF v_total_lessons > 0 AND v_completed_lessons < v_total_lessons THEN
    SET p_cert_code = NULL;
    SET p_status_code = 'NOT_ELIGIBLE';
    SET p_message = 'Ineligible: All course lessons must be completed.';
    LEAVE proc_body;
  END IF;

  -- Eligibility Check 3: All course quizzes passed
  SELECT COUNT(q.`id`) INTO v_total_quizzes
  FROM `quizzes` q
  JOIN `modules` m ON q.`module_id` = m.`id`
  WHERE m.`course_id` = v_course_id;

  IF v_total_quizzes > 0 THEN
    SELECT COUNT(DISTINCT q.`id`) INTO v_passed_quizzes
    FROM `quizzes` q
    JOIN `modules` m ON q.`module_id` = m.`id`
    JOIN `attempts` a ON a.`quiz_id` = q.`id`
    WHERE m.`course_id` = v_course_id
      AND a.`learner_id` = v_learner_id
      AND a.`is_passed` = TRUE;

    IF v_passed_quizzes < v_total_quizzes THEN
      SET p_cert_code = NULL;
      SET p_status_code = 'NOT_ELIGIBLE';
      SET p_message = 'Ineligible: All quizzes for this course must be passed.';
      LEAVE proc_body;
    END IF;
  END IF;

  START TRANSACTION;

  -- Generate unique verification code: LP-YEAR-XXXX-XXXX
  SET v_new_code = CONCAT('LP-', YEAR(NOW()), '-', UPPER(HEX(RANDOM_BYTES(3))), '-', UPPER(HEX(RANDOM_BYTES(3))));

  INSERT INTO `certificates` (`enrolment_id`, `certificate_code`, `issued_at`, `certificate_url`)
  VALUES (p_enrolment_id, v_new_code, NOW(), CONCAT('/verify/', v_new_code));

  COMMIT;

  SET p_cert_code = v_new_code;
  SET p_status_code = 'SUCCESS';
  SET p_message = 'Certificate issued successfully!';
END$$

DELIMITER ;
