import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

class AppText {
  static TextStyle h1 = GoogleFonts.inter(
    fontSize: 32, fontWeight: FontWeight.w700, color: AppColors.textPrimary,
  );
  static TextStyle h2 = GoogleFonts.inter(
    fontSize: 24, fontWeight: FontWeight.w700, color: AppColors.textPrimary,
  );
  static TextStyle h3 = GoogleFonts.inter(
    fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
  );
  static TextStyle body = GoogleFonts.inter(
    fontSize: 16, fontWeight: FontWeight.w400, color: AppColors.textPrimary,
  );
  static TextStyle bodyMuted = GoogleFonts.inter(
    fontSize: 16, fontWeight: FontWeight.w400, color: AppColors.textSecondary,
  );
  static TextStyle small = GoogleFonts.inter(
    fontSize: 15, fontWeight: FontWeight.w400, color: AppColors.textSecondary,
  );
  static TextStyle label = GoogleFonts.inter(
    fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
  );
}