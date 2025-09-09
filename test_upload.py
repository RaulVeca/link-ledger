import os
import time
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv  # ADĂUGAȚI ASTA!

# ÎNCĂRCAȚI .env ÎNAINTE DE A CITI VARIABILELE!
load_dotenv()

# Configurare
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def upload_test_file(supabase: Client, file_path: str):
    """Încarcă un fișier de test în Supabase"""
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    file_name = Path(file_path).name
    
    print(f"📤 Încărcare {file_name} în Supabase...")
    
    try:
        # Upload în bucket-ul documents
        result = supabase.storage.from_('documents').upload(
            path=file_name,
            file=file_content,
            file_options={"content-type": "application/pdf"}
        )
        print(f"✅ Fișier încărcat cu succes!")
        return file_name
    except Exception as e:
        if "already exists" in str(e):
            print(f"⚠️  Fișierul există deja. Șterg și reîncerc...")
            # Șterge fișierul existent
            supabase.storage.from_('documents').remove([file_name])
            # Reîncearcă upload
            result = supabase.storage.from_('documents').upload(
                path=file_name,
                file=file_content,
                file_options={"content-type": "application/pdf"}
            )
            print(f"✅ Fișier încărcat după ștergere!")
            return file_name
        else:
            print(f"❌ Eroare la upload: {e}")
            raise

def check_processing_result(supabase: Client, original_filename: str, max_wait: int = 60):
    """Verifică dacă fișierul a fost procesat"""
    
    base_name = Path(original_filename).stem
    json_path = f"json-output/{base_name}.json"
    
    print(f"\n⏳ Aștept procesarea... (max {max_wait} secunde)")
    print(f"   Caut rezultatul la: {json_path}")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Încearcă să descarce fișierul JSON rezultat
            result = supabase.storage.from_('documents').download(json_path)
            
            if result:
                print(f"\n✅ Procesare completă! Fișierul JSON are {len(result)} bytes")
                
                # Salvează rezultatul local pentru inspecție
                output_file = f"test_output_{base_name}.json"
                with open(output_file, 'wb') as f:
                    f.write(result)
                print(f"💾 Rezultat salvat local în: {output_file}")
                
                return True
                
        except Exception as e:
            # Fișierul nu există încă
            pass
        
        # Afișează progres
        elapsed = int(time.time() - start_time)
        print(f"\r   Timp scurs: {elapsed}s...", end="", flush=True)
        time.sleep(2)
    
    print(f"\n⏱️  Timeout! Procesarea nu s-a finalizat în {max_wait} secunde")
    return False

def main():
    """Funcția principală de test"""
    
    print("🚀 Test Sistem OCR cu Temporal\n")
    print("=" * 50)
    
    # Verifică variabilele de mediu
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Setați SUPABASE_URL și SUPABASE_SERVICE_KEY în .env!")
        return
    
    # Conectare la Supabase
    print("🔌 Conectare la Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conectat!\n")
    
    # Pregătește un fișier PDF de test
    test_pdf = "test_document.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"⚠️  Nu există {test_pdf}. Creați sau descărcați un PDF de test.")
        print("   Puteți descărca unul de test:")
        print("   wget https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf -O test_document.pdf")
        return
    
    # Upload fișier
    uploaded_file = upload_test_file(supabase, test_pdf)
    
    # Monitorizează procesarea
    success = check_processing_result(supabase, uploaded_file)
    
    if success:
        print("\n🎉 Test complet cu succes!")
        print("\n📊 Verificați:")
        print(f"   1. Temporal UI: http://localhost:8080")
        print(f"   2. Django logs în terminal")
        print(f"   3. Worker logs în terminal")
        print(f"   4. Fișierul JSON rezultat")
    else:
        print("\n❌ Testul a eșuat. Verificați:")
        print("   1. Toate serviciile rulează?")
        print("   2. Webhook-ul este configurat corect?")
        print("   3. Verificați log-urile pentru erori")

if __name__ == "__main__":
    main()