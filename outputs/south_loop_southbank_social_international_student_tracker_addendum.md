# South Loop / Southbank Social + International Student Tracker Addendum

Generated: 2026-06-17  
Scope: South Loop / Southbank apartment candidates from the tracker files, with emphasis on two F-1 international students, one applicant possibly without SSN, 2B2B under $4,000 excluding parking, two cars, in-unit W/D, gym, and garage/indoor parking.

## Safety boundary

This was a low-volume public-source scan through the browser extension and normal web pages:

- No cookies, local storage, saved passwords, account profile stores, or private messages were inspected.
- No internal social-media APIs were called.
- No bulk scrolling, mass post opening, batch comment extraction, or downloads were used.
- Facebook was treated as public-snippet-only unless content was visible without additional account interaction.
- I did not request credentials because the public information was sufficient for this tracker addendum. A deeper Facebook-group pass would require you to sign in directly in the browser and would still need to remain low-volume.

## Sources checked

### Reddit

- `r/chicagoapartments`: Coeval, Arrive LEX, 1401 S State / South Loop move-back thread, Eleven40, Alta / Grand Central, no-credit grad student rental thread.
- `r/chicago`: South Loop apartment experience thread surfaced in search, but the opened post was deleted/removed, so it is not used as substantive evidence.

### Facebook

- Public Facebook group snippet for Roosevelt Collection Lofts sublet.
- Public Facebook property/page snippets for Roosevelt Collection Lofts.
- Public South Loop / Chicago housing-group search snippets.

### Other student / international-renter platforms

- Uhouzz / 异乡好居 listing for The Reed Southbank.
- Existing Chinese-platform layer from prior Xiaohongshu screen should remain integrated separately.

## Global international-student finding

I did **not** find a public building-specific social-media post saying: “I am an F-1 international student without SSN and was approved at [specific target building].”

The strongest general application-process signal came from a Reddit thread about a grad student moving to Chicago with no credit history or job lined up:

- Source: https://www.reddit.com/r/chicagoapartments/comments/1cwzs5g/moving_to_chicago_as_a_grad_student_with_no/
- Takeaway: commenters said no credit/no income makes the search harder but not impossible; many landlords may accept co-signers, and one commenter reported a roommate with no credit/no job was able to add a co-signer through a company-managed apartment.
- Tracker implication: this supports a `cosigner_or_guarantor_required_likely` flag for no-credit/no-income applicants, but it is not building-specific proof. For F-1/no-SSN applicants, continue requiring direct leasing-office confirmation before application fees.

## Building-Level Integration

## 1. Coeval

### Social sources

- Reddit: `Experience with Coeval?`  
  https://www.reddit.com/r/chicagoapartments/comments/1cm1kp1/experience_with_coeval/
- Reddit search result also surfaced a South Loop experiences thread mentioning Coeval, but the opened post was deleted/removed and should not be used as substantive evidence.
- Xiaohongshu prior pass: `芝加哥租房 coeval公寓怎么样？`, inquiry-only, not resident review.

### Social signal

The direct Reddit Coeval thread is an inquiry, not a strong resident review. The post asks for experience at Coeval and specifically worries about noise and walls not being soundproof. The visible replies did not produce a clear resident endorsement; one commenter asked whether the original poster moved in, and another later said they chose a different building.

### International-student relevance

No Coeval-specific F-1/no-SSN approval record found. Coeval remains a plausible international-student target only because of its Greystar-linked path in the existing rescreen, not because social media proves approval.

### Tracker fields

```yaml
building: Coeval
social_sources_checked:
  - reddit
  - xiaohongshu
  - student_rental_platforms
reddit_direct_record_found: true
reddit_record_type: inquiry_not_resident_review
facebook_record_found: false
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Direct Coeval Reddit inquiry exists; concerns center on noise/wall soundproofing. No clear resident endorsement or F-1 approval proof."
social_sentiment: insufficient_mixed
social_confidence: medium_low
new_risk_flags:
  - noise_wall_soundproofing_check
  - no_ssn_path_unverified
tracker_action:
  - keep_high_priority_if_under_3500
  - require_exact_unit_noise_questions
  - require_f1_no_ssn_prequalification
```

## 2. 1400 Wabash

### Social sources

- Bing/browser search surfaced broad Reddit/forum references but no clean building-specific international-student record in this pass.
- Existing rescreen already had comparatively favorable resident-style Reddit signal and Greystar-managed application-path logic.
- Prior Xiaohongshu pass: South Loop roundup described `1400 Wabash` as new, industrial-style, rooftop gym, no pool.

### Social signal

This pass did not add a new direct Reddit/Facebook international-student record. The prior tracker logic remains: 1400 Wabash is socially favorable relative to many peers, but direct F-1/no-SSN proof is still missing.

### International-student relevance

No building-specific social proof. Treat Greystar-linked handling as a leasing-office question, not a confirmed approval path.

### Tracker fields

```yaml
building: 1400 Wabash
social_sources_checked:
  - reddit_search
  - xiaohongshu
reddit_direct_record_found: prior_only
facebook_record_found: false
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "No new direct F-1/no-SSN social proof. Prior signals remain relatively favorable; Xiaohongshu roundup frames it as new/industrial with rooftop gym."
social_sentiment: positive_mixed_insufficient
social_confidence: medium_low
new_risk_flags:
  - no_ssn_path_unverified
  - two_parking_spaces_unverified
tracker_action:
  - keep_high_priority_if_under_4000
  - high_priority_if_under_3500
  - prequalify_greystar_no_ssn_documents
```

## 3. 1401 S State

### Social sources

- Reddit: `Moving back to the city`  
  https://www.reddit.com/r/chicagoapartments/comments/1bf4wq7/moving_back_to_the_city/
- Xiaohongshu prior pass: South Loop roundup said `1401 S State` has larger units, higher utilities, and transit proximity.

### Social signal

The Reddit thread is not an international-student thread, but it gives useful apartment-shopping signal. The poster toured 1401 S State, liked its vibe and floor-to-ceiling windows, but found the lease/holding-fee option over budget. The same thread also lists Arrive LEX, 1400 Wabash, and AMLI 900 as comparison targets.

Xiaohongshu independently reinforces the `utility_cost_risk`: `1401 S State` was described as large units, higher utilities, and close to transit.

### International-student relevance

No 1401-specific F-1/no-SSN approval record found. Because it is Greystar-linked in the existing rescreen, it remains plausible but must be verified directly.

### Tracker fields

```yaml
building: 1401 S State
social_sources_checked:
  - reddit
  - xiaohongshu
reddit_direct_record_found: true
reddit_record_type: shopper_tour_signal
facebook_record_found: false
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Reddit shopper liked the vibe/windows but price/holding fee was over budget. Xiaohongshu flags large units, higher utilities, and transit proximity."
social_sentiment: mixed_positive_price_caution
social_confidence: medium
new_risk_flags:
  - utility_cost_risk
  - holding_fee_or_price_term_check
  - transit_noise_check
tracker_action:
  - keep_top_target_if_total_monthly_under_3500
  - require_total_monthly_cost_breakdown
  - require_exact_lease_term_and_fee_review
  - require_f1_no_ssn_prequalification
```

## 4. AMLI 900

### Social sources

- Reddit search found AMLI/South Loop-adjacent threads, but no new AMLI 900 F-1/no-SSN resident record.
- Existing rescreen already includes AMLI policy clarity and social noise/thin-wall caution.
- AMLI 900 appears as a comparison target in the 1401 S State / South Loop Reddit shopping thread.

### Social signal

No new direct AMLI 900 social evidence changed the existing tracker conclusion. AMLI 900 remains strongest on application-policy clarity, not on social enthusiasm or price.

### International-student relevance

Existing AMLI policy clarity remains more useful than social media for this building. Still, property-level confirmation is required.

### Tracker fields

```yaml
building: AMLI 900
social_sources_checked:
  - reddit_search
  - existing_policy_rescreen
reddit_direct_record_found: no_new_record
facebook_record_found: false
international_student_record_found: policy_level_not_social
no_ssn_approval_record_found: policy_level_not_building_specific
social_signal_summary: "No new social proof. Keep as policy-clarity fallback; prior noise/thin-wall caution remains."
social_sentiment: policy_positive_social_mixed
social_confidence: medium
new_risk_flags:
  - price_above_preferred_budget
  - noise_wall_check
tracker_action:
  - keep_as_safe_application_path_target
  - notify_under_3700_or_large_layout_under_4000
  - confirm_student_no_ssn_document_package
```

## 5. Roosevelt Collection Lofts

### Social sources

- Facebook public property/page snippet:  
  https://www.facebook.com/LoftsatRooseveltCollection/
- Facebook public group post snippet:  
  https://www.facebook.com/groups/398873787655488/posts/1691304378412416/
- Xiaohongshu prior direct note: `家楼下就是商圈是种什么样的体验`

### Social signal

Facebook public snippet for a June 2025 sublet says a resident was seeking someone to take over a full 2x2 at Roosevelt Collection Lofts. The visible content says base rent was $2,888, utilities included except electric and Wi-Fi, lease through August 27, 2025 with possible renewal, full gym and amenities, and the building was well-maintained. This is a meaningful resident/sublet-style signal, but it is still a single sublet post, not a formal lease quote.

The Facebook property/page snippet shows an active property page and public social presence. Xiaohongshu content reinforces the lifestyle convenience: shopping, AMC, Target/Whole Foods/Roosevelt station proximity, indoor W/D, gym, and indoor garage.

### International-student relevance

No F-1/no-SSN approval record found. However, visible sublet activity may matter if official new-lease approval is hard, because lease takeover/sublet paths can have different approval requirements.

### Tracker fields

```yaml
building: Roosevelt Collection Lofts
social_sources_checked:
  - facebook
  - xiaohongshu
  - reddit_search
facebook_record_found: true
facebook_record_type: public_sublet_post_and_property_page
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Public Facebook sublet showed a 2x2 at $2,888 base rent in 2025, with gym/amenities and well-maintained resident wording. Xiaohongshu confirms lifestyle convenience."
social_sentiment: positive_lifestyle_value
social_confidence: medium
new_risk_flags:
  - sublet_price_not_current_official_price
  - f1_path_unverified
  - two_parking_spaces_unverified
tracker_action:
  - keep_top_value_lifestyle_watch
  - track_official_new_lease_and_sublet_channels_separately
  - confirm_new_lease_vs_takeover_requirements
```

## 6. Aspire

### Social sources

- Reddit search surfaced broad South Loop apartment threads, but not a clear Aspire-specific resident or international-student record.
- Xiaohongshu prior pass only had roundup-level mention: near Chinatown direction, golf simulator.

### Social signal

This pass did not surface a building-specific Aspire social proof point. Treat Aspire as strong on official pricing/building fit, weak on social/application evidence.

### International-student relevance

No Aspire-specific F-1/no-SSN proof found. Existing caution about potential guarantor requirements remains.

### Tracker fields

```yaml
building: Aspire
social_sources_checked:
  - reddit_search
  - xiaohongshu
reddit_direct_record_found: false
facebook_record_found: false
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "No direct social/application record found. Only generic South Loop and Xiaohongshu roundup signals."
social_sentiment: insufficient_neutral
social_confidence: low
new_risk_flags:
  - guarantor_requirement_unknown
  - no_ssn_path_unverified
tracker_action:
  - keep_conditional_high_value
  - do_not_mark_application_ready_until_us_guarantor_requirement_known
```

## 7. Arrive LEX

### Social sources

- Reddit: `Anyone living at Arrive lex?`  
  https://www.reddit.com/r/chicagoapartments/comments/175npgo/anyone_living_at_arrive_lex/
- Reddit: `Moving back to the city` includes Arrive LEX in a South Loop comparison list.  
  https://www.reddit.com/r/chicagoapartments/comments/1bf4wq7/moving_back_to_the_city/
- Xiaohongshu prior pass had Arrive-related content, but many results mixed Arrive LEX with Arrive Michigan / Arrive Streeterville.

### Social signal

The Arrive LEX Reddit thread was partially deleted, but visible replies are not strongly negative about Arrive LEX itself. One commenter helped someone move in and said staff seemed nice/helpful during the first two weeks, but had no later experience. Another reply discussed Arrive Streeterville, not Arrive LEX, and should not be transferred directly.

The bigger issue is source confusion: social search easily mixes Arrive LEX, Arrive Michigan, and Arrive Streeterville.

### International-student relevance

No F-1/no-SSN approval record found. Arrive LEX remains attractive on price but not proven on application path.

### Tracker fields

```yaml
building: Arrive LEX
social_sources_checked:
  - reddit
  - xiaohongshu
reddit_direct_record_found: true
reddit_record_type: weak_move_in_secondhand_signal
facebook_record_found: false
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Arrive LEX Reddit thread has weak/limited direct signal; visible replies are not conclusive. High risk of confusing LEX with Arrive Michigan or Streeterville."
social_sentiment: mixed_insufficient
social_confidence: medium_low
new_risk_flags:
  - arrive_brand_building_confusion
  - application_path_unknown
  - parking_security_confirm
tracker_action:
  - keep_conditional_value_target
  - notify_under_3400_high_priority
  - require_building_specific_reviews_only
  - require_f1_no_ssn_and_two_parking_confirmation
```

## 8. Eleven40

### Social sources

- Reddit: `Has anyone lived at Eleven40 apartments in the South Loop?`  
  https://www.reddit.com/r/chicagoapartments/comments/15b6amu/has_anyone_lived_at_eleven40_apartments_in_the/
- Xiaohongshu prior pass: direct negative resident-style note about move-in condition and management response.

### Social signal

The Reddit thread is partly deleted but visible replies focus more on the Roosevelt/State area than the building itself. One nearby resident called the area great but warned Roosevelt and State can feel sketchy and requires situational awareness, especially late at night. Another commenter said the building was new, location solid, and unlikely to be an “absolute bust” unless reviews showed developer problems, but still advised using broader review sources.

The Xiaohongshu direct resident-style note remains the stronger negative signal: move-in cleanliness/appliance-readiness and management response problems.

### International-student relevance

No F-1/no-SSN approval record found. Social risk is higher than the top targets.

### Tracker fields

```yaml
building: Eleven40
social_sources_checked:
  - reddit
  - xiaohongshu
reddit_direct_record_found: true
reddit_record_type: area_safety_and_general_building_inquiry
xhs_direct_negative_record_found: true
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Reddit flags Roosevelt/State situational-awareness risk. Xiaohongshu flags move-in condition and management response risk."
social_sentiment: mixed_negative
social_confidence: medium
new_risk_flags:
  - roosevelt_state_late_night_awareness
  - move_in_condition_risk
  - appliance_readiness_risk
  - management_response_risk
tracker_action:
  - downgrade_to_caution_watchlist
  - notify_only_if_under_3500_or_exceptionally_strong_unit
  - require_recent_unit_condition_tour
```

## 9. The Reed at Southbank

### Social sources

- Uhouzz / 异乡好居 student-rental listing:  
  https://www.uhouzz.com/us/chicago/detail-apartments-1567688
- Existing Xiaohongshu prior pass: The Reed appears in Chinese/student-rental and Southbank-lifestyle contexts.

### Social signal

Uhouzz lists The Reed Southbank as a social apartment with 0 service fee, gym, 224 suites, built in 2023, in-unit washer/dryer, fitness center, coworking, rooftop/pool/spa-style amenities, and 2B2B availability category. It also frames nearby schools such as DePaul Loop, Columbia College, Roosevelt University, and Robert Morris as walkable.

This is useful international-student platform visibility, not an independent resident review.

### International-student relevance

The platform is student/international-renter oriented, which helps market visibility, but it does not prove no-SSN approval or F-1 document acceptance at the property.

### Tracker fields

```yaml
building: The Reed at Southbank
social_sources_checked:
  - uhouzz
  - xiaohongshu
student_platform_record_found: true
reddit_direct_record_found: false
international_student_record_found: student_platform_visibility_only
no_ssn_approval_record_found: false
social_signal_summary: "Uhouzz/Chinese student-rental platform lists The Reed with modern amenities and 2B2B category; strong student-market visibility but no approval proof."
social_sentiment: positive_lifestyle_student_visibility
social_confidence: medium_low
new_risk_flags:
  - price_stretch
  - no_ssn_path_unverified
  - two_parking_spaces_unverified
tracker_action:
  - keep_southbank_lifestyle_stretch
  - notify_under_3800_high_priority
  - require_official_price_and_parking_confirmation
```

## 10. The Grand Central / Alta Grand Central

### Social sources

- Reddit: `Alta at Grand Central`  
  https://www.reddit.com/r/chicagoapartments/comments/1ftcf0d/alta_at_grand_central/

### Social signal

The Reddit thread asks about safety around The Grand Central / Alta at 221 W Harrison. Visible replies say the area is safe or pretty safe, busy during the day and quiet at night, with the main caution that the building is next to the 290/90/94 interchange, so traffic/noise can be an issue.

### International-student relevance

No F-1/no-SSN approval record found. The building remains a watchlist option if price and highway-noise exposure are acceptable.

### Tracker fields

```yaml
building: The Grand Central / Alta Grand Central
social_sources_checked:
  - reddit
reddit_direct_record_found: true
reddit_record_type: area_safety_inquiry
international_student_record_found: false
no_ssn_approval_record_found: false
social_signal_summary: "Reddit replies describe the area as safe/pretty safe; main caution is highway/interchange noise."
social_sentiment: neutral_positive_area_noise_caution
social_confidence: medium
new_risk_flags:
  - highway_interchange_noise
  - nighttime_quiet_area
  - no_ssn_path_unverified
tracker_action:
  - keep_watchlist
  - notify_under_3500_high_priority
  - require_unit_orientation_noise_check
```

## Facebook Group Signals

The public search surface found multiple Chicago/South Loop housing groups, including:

- `South Loop - Housing, Rooms, Apartments, Sublets, ...`
- `CHICAGO Housing, Rooms, Apartments, Sublets, ...`
- `Chicago Apartments & Housing`

These groups are relevant for sublets and lease takeovers, but most group content is login-gated or only partially visible. The only useful building-specific Facebook post visible in this pass was the Roosevelt Collection Lofts 2x2 sublet.

Tracker treatment:

```yaml
facebook_group_monitoring:
  allowed_mode: manual_low_volume
  credential_required_for_deeper_scan: true
  credential_instruction: "User should sign in directly in browser; do not send credentials in chat."
  buildings_with_visible_fb_signal:
    - Roosevelt Collection Lofts
  use_cases:
    - sublet_price_reference
    - lease_takeover_signal
    - two_bedroom_liquidity_signal
  caveats:
    - not official availability
    - not proof of F-1/no-SSN approval
    - sublet rules may differ from new-lease rules
```

## International Student Tracker Rules

Add these fields to every building:

```yaml
social_sources_checked:
reddit_direct_record_found:
reddit_record_type:
facebook_record_found:
facebook_record_type:
student_platform_record_found:
international_student_record_found:
no_ssn_approval_record_found:
cosigner_or_guarantor_required_likely:
third_party_guarantor_possible_but_unconfirmed:
social_signal_summary:
social_sentiment:
social_confidence:
new_risk_flags:
application_ready:
```

Set `application_ready: false` unless all of the following are confirmed by the leasing office:

```yaml
no_ssn_applicant_allowed: true
f1_documents_allowed: true
proof_of_funds_allowed: true
combined_household_qualification_allowed: true
us_based_guarantor_required: false
or_third_party_guarantor_allowed: true
two_garage_spaces_confirmed: true
```

## Scoring Updates

```yaml
reddit_direct_positive_resident_record: +8
reddit_direct_inquiry_only: 0
reddit_area_safety_caution: -5
facebook_sublet_positive_resident_record: +6
student_platform_visibility: +4
student_platform_visibility_only_no_review: 0
building_name_confusion_risk: -8
move_in_condition_complaint: -12
management_response_complaint: -10
utility_cost_social_flag: -6
highway_or_transit_noise_social_flag: -6
f1_no_ssn_record_found: +25
f1_no_ssn_record_not_found: 0
cosigner_likely_required: -10
no_direct_application_path: -15
```

## Revised Social/Application Priority

1. **Coeval**  
   Still high priority for price/actionability, but social proof is weaker than the prior ranking implies. Add noise/wall check and do not treat Reddit as positive resident proof.

2. **1400 Wabash**  
   Still strong due to Greystar/newer-building logic, but no new F-1/no-SSN social proof. Keep high priority if under $4,000 and two parking spaces are possible.

3. **1401 S State**  
   Keep top target, but social signals reinforce total-cost/utility and lease-term scrutiny.

4. **Roosevelt Collection Lofts**  
   Strongest Facebook/sublet/lifestyle social signal in this pass. Good value/lifestyle watch, but official new-lease approval path remains unverified.

5. **AMLI 900**  
   Best application-policy fallback from existing rescreen, but little new social signal. Keep for policy clarity, not price.

6. **Aspire**  
   Conditional. Good price/building fit, weak social and application evidence.

7. **Arrive LEX**  
   Conditional. Good price, but social evidence is limited and easily confused with other Arrive properties.

8. **The Reed**  
   Southbank lifestyle stretch with Chinese/student-rental platform visibility; no no-SSN proof.

9. **The Grand Central / Alta**  
   Watchlist. Social signal says area is generally safe, with highway/interchange noise as the main issue.

10. **Eleven40**  
   Caution watchlist. Reddit flags area awareness; Xiaohongshu flags move-in/management issues.

## Bottom Line

The social/international-student scan still finds **no building-specific public proof** that a no-SSN F-1 applicant was approved at any target building. The tracker should therefore separate:

- `unit_fit`: price, 2B2B, W/D, gym, parking.
- `social_fit`: resident/social risk.
- `application_fit`: F-1/no-SSN, proof of funds, guarantor rules.

The best new actionable social signal is Roosevelt Collection Lofts’ visible Facebook 2x2 sublet, which supports value/liquidity but not new-lease approval. The most useful general application signal is the Reddit no-credit grad-student thread, which supports preparing for a cosigner/guarantor path.
