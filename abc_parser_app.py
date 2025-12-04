import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Any
from pathlib import Path

# ==========================================
# PART 1: Database & Parsing Logic
# ==========================================

class TuneDatabase:
    """Handles all SQL interactions using SQLite."""

    def __init__(self, db_name: str = "tunes.db"):
        """Initialize database connection and schema."""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self) -> None:
        """Creates the tunes table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tunes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                reference_number TEXT,
                title TEXT,
                rhythm TEXT,
                key_sig TEXT,
                content TEXT
            )
        """)
        self.conn.commit()

    def insert_tune(self, tune_data: Dict[str, Any]) -> None:
        """
        Inserts a single tune dictionary into the database.
        
        Args:
            tune_data: Dictionary containing tune details.
        """
        self.cursor.execute("""
            INSERT INTO tunes (book_id, reference_number, title, rhythm, key_sig, content)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tune_data.get('book_id'),
            tune_data.get('X'),
            tune_data.get('T', 'Unknown'),
            tune_data.get('R', 'Unknown'),
            tune_data.get('K', 'Unknown'),
            tune_data.get('content', '')
        ))
        self.conn.commit()

    def close(self) -> None:
        """Closes the database connection."""
        self.conn.close()


def parse_abc_file(filepath: Path, book_id: int) -> List[Dict[str, Any]]:
    """
    Parses a single ABC file and returns a list of tunes.
    
    Args:
        filepath: Path object pointing to the file.
        book_id: Integer representing the book folder.
        
    Returns:
        List of dictionaries, where each dict is a tune.
    """
    tunes = []
    current_tune = {}
    in_tune = False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if a new tune is starting (X: indicates start)
            if line.startswith("X:"):
                # If we were already parsing a tune, save the previous one
                if current_tune:
                    tunes.append(current_tune)
                
                # Start new tune
                current_tune = {'book_id': book_id, 'content': line + '\n'}
                current_tune['X'] = line.split(':')[1].strip()
                in_tune = True
                
            elif in_tune:
                # Append line to raw content
                current_tune['content'] += line + '\n'
                
                # Parse Headers
                if line.startswith("T:"):
                    # Only take the first title if multiple exist
                    if 'T' not in current_tune: 
                        current_tune['T'] = line.split(':')[1].strip()
                elif line.startswith("R:"):
                    current_tune['R'] = line.split(':')[1].strip()
                elif line.startswith("K:"):
                    current_tune['K'] = line.split(':')[1].strip()
                    
        # Don't forget the very last tune in the file
        if current_tune:
            tunes.append(current_tune)
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return tunes


def process_directory(base_path: str, db: TuneDatabase) -> int:
    """
    Recursively walks directory, parses files, and saves to DB.
    
    Returns:
        Total number of tunes processed.
    """
    total_tunes = 0
    path_obj = Path(base_path)
    
    # Walk through directory
    for file_path in path_obj.rglob('*.abc'):
        # Extract book number from parent folder name
        try:
            parent_folder = file_path.parent.name
            book_id = int(parent_folder)
        except ValueError:
            print(f"Skipping {file_path}: Parent folder '{file_path.parent.name}' is not a valid number.")
            continue
            
        # Parse
        tunes_found = parse_abc_file(file_path, book_id)
        
        # Insert
        for tune in tunes_found:
            db.insert_tune(tune)
            
        total_tunes += len(tunes_found)
        print(f"Processed Book {book_id}: {file_path.name} ({len(tunes_found)} tunes)")
        
    return total_tunes


# ==========================================
# PART 2: Pandas Analysis Logic
# ==========================================

class TuneAnalyzer:
    """Handles loading data into Pandas and running queries."""
    
    def __init__(self, db_name: str = "tunes.db"):
        self.conn = sqlite3.connect(db_name)
        
    def load_data(self) -> pd.DataFrame:
        """Loads entire SQL table into a DataFrame."""
        query = "SELECT * FROM tunes"
        return pd.read_sql(query, self.conn)
    
    def get_tunes_by_book(self, df: pd.DataFrame, book_id: int) -> pd.DataFrame:
        """Filter dataframe by book ID."""
        return df[df['book_id'] == book_id]
    
    def get_tunes_by_rhythm(self, df: pd.DataFrame, rhythm: str) -> pd.DataFrame:
        """Filter dataframe by rhythm type."""
        # Case insensitive string contains
        return df[df['rhythm'].str.contains(rhythm, case=False, na=False)]
    
    def search_tunes(self, df: pd.DataFrame, search_term: str) -> pd.DataFrame:
        """Search titles for a specific term."""
        return df[df['title'].str.contains(search_term, case=False, na=False)]

    def plot_key_distribution(self, df: pd.DataFrame) -> None:
        """Optional: Visualise the keys used in the books."""
        if df.empty:
            print("No data to plot.")
            return
            
        counts = df['key_clean'].value_counts().head(10) # Show top 10
        counts.plot(kind='bar', color='skyblue')
        plt.title('Distribution of Musical Keys')
        plt.xlabel('Key')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.show()

# ==========================================
# PART 3: Interactive UI (CLI) - ***FIXED MAIN FUNCTION***
# ==========================================

def print_menu():
    print("\n--- ABC TUNE MANAGER ---")
    print("1. Re-scan folders and Populate Database")
    print("2. Show Statistics (Pandas Load)")
    print("3. Search by Title")
    print("4. List Tunes by Book")
    print("5. [Optional] Plot Key Distribution")
    print("6. Exit")

# Use a global variable for the DataFrame to ensure all functions see updates
df = pd.DataFrame() 

def main():
    global df # Declare intent to modify the global df variable
    db_name = "tunes.db"
    analyzer = TuneAnalyzer(db_name)
    
    print("Attempting initial data load...")
    try:
        # Load any existing data from the DB file
        df = analyzer.load_data()
        print(f"Successfully loaded {len(df)} tunes into a DataFrame.")
    except Exception as e:
        # Only print the error if it's not the 'no such table' error
        if "no such table" not in str(e):
             print(f"Initial DB load failed: {e}")

    if df.empty:
        print("\nNote: DataFrame is currently empty. Please run Option 1.")

    while True:
        print_menu()
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            print("\nScanning 'abc_books' directory...")
            # Clear old data by deleting and recreating the DB file
            if os.path.exists(db_name):
                os.remove(db_name)
            
            db = TuneDatabase(db_name)
            count = process_directory("abc_books", db)
            db.close()
            print(f"\nSuccess! {count} tunes imported.")
            
            # ***CRITICAL FIX***: Reload the global DataFrame immediately after import
            df = analyzer.load_data() 
            print(f"Successfully loaded {len(df)} tunes into DataFrame for analysis.")
            
        elif choice == '2':
            if df.empty:
                print("Data not loaded. Please Run Option 1.")
                continue
            print("\n--- Data Statistics ---")
            print(f"Total Tunes Loaded: {len(df)}")
            print(f"Unique Book IDs: {df['book_id'].nunique()}")
            print("\n--- First 5 Rows ---")
            # Ensure index=False is used for cleaner output
            print(df[['book_id', 'title', 'rhythm', 'key_sig']].head().to_string(index=False))
            
        elif choice == '3':
            if df.empty: print("Data empty. Run Option 1."); continue
            term = input("Enter search term (Title): ")
            results = analyzer.search_tunes(df, term)
            print(f"\nFound {len(results)} matches:")
            print(results[['title', 'book_id', 'rhythm', 'key_sig']].to_string(index=False))
            
        elif choice == '4':
            if df.empty: print("Data empty. Run Option 1."); continue
            try:
                bid = int(input("Enter Book Number to view: "))
                results = analyzer.get_tunes_by_book(df, bid)
                print(f"\n--- Book {bid} ({len(results)} tunes) ---")
                print(results[['reference_number', 'title', 'rhythm', 'key_sig']].to_string(index=False))
            except ValueError:
                print("Please enter a valid number.")

        elif choice == '5':
            if df.empty: print("Data empty. Run Option 1."); continue
            print("Generating plot...")
            analyzer.plot_key_distribution(df)
            
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()
