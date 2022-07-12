Feature: Location management
  As a clinician
  I want to create and retrieve many locations
  So that I can manage patient care

  Background:
    Given a valid JWT

  # Increase these numbers for performance testing. e.g. 2, 100, 10, 5 gives 10,000 locations
  Scenario: Many locations are created
    Given 4 hospitals each with 10 wards each with 10 bays and 5 beds exists
    When timing this step
    And we fetch the location hierarchy
    Then it took less than 2 seconds to complete
    And we received all of the expected locations
