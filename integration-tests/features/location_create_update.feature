Feature: Location management
  As a clinician
  I want to create and update locations
  So that I can manage patient care

  Background:
    Given a valid JWT

  Scenario: Hospital is created
    Given a hospital called "Sycamore" exists
    Then the location creation response is correct

  Scenario: Hospital hierarchy is created
    Given a hospital called "Sycamore" exists
    Then the location creation response is correct
    When a ward "Apple" is created in "Sycamore"
    And a bay "Bay1" is created in "Apple"
    Then location "Bay1" has parents "Apple, Sycamore"

  Scenario: Location is updated
    Given a hospital called "Ceres" exists
    When a ward "Tycho" is created in "Ceres"
    And the "Tycho" ward's default score system is updated to meows
    Then the resulting location has the expected default score system of meows

  Scenario: Organisation is created
    When an Organisation "Group One" is created
    Then the location creation response is correct 
